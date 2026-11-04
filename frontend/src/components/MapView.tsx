import { useEffect, useRef, useState } from 'react';
import maplibregl from 'maplibre-gl';
import type {
  Feature as GeoJSONFeature,
  FeatureCollection as GeoJSONFeatureCollection,
  LineString as GeoJSONLineString,
  Point as GeoJSONPoint,
} from 'geojson';
import type { Camera, Trajectory } from '../types';
import { confidenceRatio, formatDateTime, segmentTier } from '../lib/format';

const DARK_STYLE_URL = 'https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json';

interface Props {
  cameras: Camera[];
  trajectories: Trajectory[];
  selectedVehicleId?: string;
  highlightedCameraIds: string[];
  /** Camera to mark with the larger pulsing "current position" ring —
   * distinct from highlightedCameraIds, which are the amber alert-range glow. */
  focusedCameraId?: string;
  /** Set (to a new value) to pan/zoom the map to a specific camera — used by
   * the Cameras tab and the camera filter, independent of vehicle selection. */
  flyToCameraId?: string;
  onSelectCamera?: (camera: Camera) => void;
}

function cameraFeatureCollection(cameras: Camera[], highlighted: Set<string>) {
  return {
    type: 'FeatureCollection' as const,
    features: cameras.map((c) => ({
      type: 'Feature' as const,
      geometry: { type: 'Point' as const, coordinates: [c.longitude, c.latitude] },
      properties: {
        camera_id: c.camera_id,
        road_segment: c.road_segment,
        status: c.status,
        installed_at: c.installed_at,
        highlighted: highlighted.has(c.camera_id),
      },
    })),
  };
}

function trajectoryFeatureCollection(trajectories: Trajectory[]) {
  const features: GeoJSONFeature<GeoJSONLineString>[] = [];
  for (const traj of trajectories) {
    if (!traj.route_geometry) continue;
    for (const seg of traj.route_geometry) {
      if (!seg.points || seg.points.length < 2) continue;
      // Find matching transition to get status/confidence
      const t = traj.transitions.find(
        (tr) => tr.from_camera_id === seg.from_camera_id && tr.to_camera_id === seg.to_camera_id
      );
      features.push({
        type: 'Feature',
        geometry: {
          type: 'LineString',
          coordinates: seg.points.map((p) => [p.lon, p.lat]),
        },
        properties: {
          status: t ? t.status : 'INFERRED',
          tier: t ? segmentTier(t.status) : 2,
          confidence: t ? confidenceRatio(t.confidence) : 0.5,
        },
      });
    }
  }
  return { type: 'FeatureCollection' as const, features };
}

/** Finds the most recent observation across every returned trajectory for a
 * vehicle, so the map can fall back to a single-point flyTo even when a
 * route has no transitions yet (e.g. a vehicle seen at only one camera). */
function latestObservationCoord(
  trajectories: Trajectory[],
  cameras: Camera[],
): [number, number] | undefined {
  let best: { time: number; cameraId: string } | undefined;
  for (const traj of trajectories) {
    for (const o of traj.observations) {
      const t = Date.parse(o.timestamp);
      if (!best || t > best.time) best = { time: t, cameraId: o.camera_id };
    }
  }
  if (!best) return undefined;
  const cam = cameras.find((c) => c.camera_id === best!.cameraId);
  return cam ? [cam.longitude, cam.latitude] : undefined;
}

export function MapView({
  cameras,
  trajectories,
  selectedVehicleId,
  highlightedCameraIds,
  focusedCameraId,
  flyToCameraId,
  onSelectCamera,
}: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<maplibregl.Map | null>(null);
  const popupRef = useRef<maplibregl.Popup | null>(null);
  const focusMarkerRef = useRef<maplibregl.Marker | null>(null);
  const readyRef = useRef(false);
  const [mapError, setMapError] = useState<string>();

  // Init map once.
  useEffect(() => {
    if (!containerRef.current) return;

    let map: maplibregl.Map;
    try {
      map = new maplibregl.Map({
        container: containerRef.current,
        style: DARK_STYLE_URL,
        center: [77.5946, 12.9716],
        zoom: 12,
        pitch: 55,
        bearing: -12,
        maxPitch: 75,
        attributionControl: {
          compact: true,
          customAttribution:
            '© <a href="https://carto.com/attributions" target="_blank" rel="noopener">CARTO</a> © <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener">OpenStreetMap</a> contributors',
        },
      });
    } catch (err) {
      // MapLibre throws synchronously here if it can't get a WebGL context
      // (unsupported browser/GPU/driver) — surface it instead of a blank canvas.
      setMapError(
        err instanceof Error
          ? err.message
          : 'The map could not start a WebGL context on this device.',
      );
      return;
    }

    // Non-fatal tile/style errors still get logged; a style-load failure
    // (e.g. basemap host unreachable) is surfaced in the UI rather than
    // left as a silent black rectangle.
    map.on('error', (e) => {
      console.error('MapLibre error:', e.error);
      if (!readyRef.current) {
        setMapError(e.error?.message ?? 'The map failed to load.');
      }
    });

    map.addControl(new maplibregl.NavigationControl({ visualizePitch: true }), 'bottom-right');
    mapRef.current = map;
    popupRef.current = new maplibregl.Popup({ closeButton: false, offset: 12 });

    map.on('load', () => {
      // Directional light so extruded buildings read as 3D volumes rather
      // than flat tinted shapes.
      map.setLight({ anchor: 'viewport', color: '#e0b98f', intensity: 0.35, position: [1.5, 80, 40] });

      // 3D building extrusions, built from the basemap's own vector building
      // layer. CARTO's schema doesn't guarantee a height field on every
      // building, so we fall back to a plausible uniform height rather than
      // leaving those buildings flat or invisible.
      const beforeId = map.getLayer('boundary_country_outline') ? 'boundary_country_outline' : undefined;
      if (map.getSource('carto')) {
        map.addLayer(
          {
            id: '3d-buildings',
            type: 'fill-extrusion',
            source: 'carto',
            'source-layer': 'building',
            minzoom: 13,
            paint: {
              'fill-extrusion-color': '#1a3348',
              'fill-extrusion-height': [
                'coalesce',
                ['get', 'render_height'],
                ['get', 'height'],
                12,
              ],
              'fill-extrusion-base': [
                'coalesce',
                ['get', 'render_min_height'],
                ['get', 'min_height'],
                0,
              ],
              'fill-extrusion-opacity': 0.85,
              'fill-extrusion-vertical-gradient': true,
            },
          },
          beforeId,
        );
      }

      map.addSource('cameras', {
        type: 'geojson',
        data: cameraFeatureCollection([], new Set()),
      });

      map.addLayer({
        id: 'camera-glow',
        type: 'circle',
        source: 'cameras',
        filter: ['==', ['get', 'highlighted'], true],
        paint: {
          'circle-radius': 14,
          'circle-color': '#e8b83f',
          'circle-opacity': 0.25,
          'circle-blur': 0.6,
        },
      });

      // Dark halo under every pin so it stays legible against bright
      // building facades or busy basemap detail in the tilted 3D view.
      map.addLayer({
        id: 'camera-halo',
        type: 'circle',
        source: 'cameras',
        paint: {
          'circle-radius': ['case', ['get', 'highlighted'], 10, 8],
          'circle-color': '#020c1a',
          'circle-opacity': 0.7,
        },
      });

      map.addLayer({
        id: 'camera-points',
        type: 'circle',
        source: 'cameras',
        paint: {
          'circle-radius': ['case', ['get', 'highlighted'], 7, 5],
          'circle-color': [
            'match',
            ['get', 'status'],
            'active',
            '#3f7f9c',
            'offline',
            '#4a5a6b',
            '#9fb3c2',
          ],
          'circle-stroke-width': ['case', ['get', 'highlighted'], 2, 1],
          'circle-stroke-color': ['case', ['get', 'highlighted'], '#e8b83f', '#020c1a'],
        },
      });

      map.addSource('trajectories', {
        type: 'geojson',
        data: trajectoryFeatureCollection([]),
      });

      // Dark, wider halo beneath all segment types so trajectory lines
      // read clearly against extruded buildings and dense road geometry,
      // regardless of what's directly underneath them.
      map.addLayer({
        id: 'trajectory-halo',
        type: 'line',
        source: 'trajectories',
        layout: { 'line-cap': 'round', 'line-join': 'round' },
        paint: {
          'line-color': '#020c1a',
          'line-width': ['interpolate', ['linear'], ['get', 'confidence'], 0, 4, 1, 8],
          'line-opacity': 0.55,
        },
      });

      // Confirmed segments: solid, thickness/opacity scale with confidence.
      map.addLayer({
        id: 'trajectory-confirmed',
        type: 'line',
        source: 'trajectories',
        filter: ['==', ['get', 'tier'], 'confirmed'],
        layout: { 'line-cap': 'round', 'line-join': 'round' },
        paint: {
          'line-color': '#5ba7c4',
          'line-width': ['interpolate', ['linear'], ['get', 'confidence'], 0, 2, 1, 5],
          'line-opacity': ['interpolate', ['linear'], ['get', 'confidence'], 0, 0.35, 1, 0.95],
        },
      });

      // Inferred segments: dashed amber, thinner and dimmer, confidence-scaled.
      map.addLayer({
        id: 'trajectory-inferred',
        type: 'line',
        source: 'trajectories',
        filter: ['==', ['get', 'tier'], 'inferred'],
        layout: { 'line-cap': 'round', 'line-join': 'round' },
        paint: {
          'line-color': '#e8b83f',
          'line-width': ['interpolate', ['linear'], ['get', 'confidence'], 0, 1.5, 1, 3.5],
          'line-opacity': ['interpolate', ['linear'], ['get', 'confidence'], 0, 0.25, 1, 0.75],
          'line-dasharray': [2, 2],
        },
      });

      // Uncertain segments: any status other than CONFIRMED/INFERRED the
      // backend might send — finely dotted and rose-tinted so a genuinely
      // low-confidence hop reads as visually distinct from "inferred".
      map.addLayer({
        id: 'trajectory-uncertain',
        type: 'line',
        source: 'trajectories',
        filter: ['==', ['get', 'tier'], 'uncertain'],
        layout: { 'line-cap': 'round', 'line-join': 'round' },
        paint: {
          'line-color': '#d65118',
          'line-width': ['interpolate', ['linear'], ['get', 'confidence'], 0, 1.5, 1, 3],
          'line-opacity': ['interpolate', ['linear'], ['get', 'confidence'], 0, 0.25, 1, 0.7],
          'line-dasharray': [0.5, 2],
        },
      });

      map.on('mouseenter', 'camera-points', () => {
        map.getCanvas().style.cursor = 'pointer';
      });
      map.on('mouseleave', 'camera-points', () => {
        map.getCanvas().style.cursor = '';
        popupRef.current?.remove();
      });
      map.on('mousemove', 'camera-points', (e) => {
        const f = e.features?.[0];
        if (!f || !popupRef.current) return;
        const geom = f.geometry as GeoJSONPoint;
        const p = f.properties as {
          camera_id: string;
          road_segment: string;
          status: string;
          installed_at: string;
        };
        const installed = p.installed_at ? formatDateTime(p.installed_at) : 'unknown';
        popupRef.current
          .setLngLat(geom.coordinates as [number, number])
          .setHTML(
            `<div style="font-family:'IBM Plex Sans',sans-serif;min-width:150px">
               <div style="font-size:12px;font-weight:600;margin-bottom:2px">${p.camera_id}</div>
               <div style="font-size:11px;color:#9fb3c2">${p.road_segment}</div>
               <div style="font-size:10px;margin-top:4px;color:${p.status === 'active' ? '#3f7f9c' : '#4a5a6b'}">${p.status}</div>
               <div style="font-size:10px;margin-top:2px;color:#6d8a9a">Installed ${installed}</div>
             </div>`,
          )
          .addTo(map);
      });
      map.on('click', 'camera-points', (e) => {
        const f = e.features?.[0];
        if (!f || !onSelectCamera) return;
        const p = f.properties as { camera_id: string; road_segment: string; status: string };
        onSelectCamera({
          camera_id: p.camera_id,
          road_segment: p.road_segment,
          status: p.status as Camera['status'],
          latitude: (f.geometry as GeoJSONPoint).coordinates[1],
          longitude: (f.geometry as GeoJSONPoint).coordinates[0],
          installed_at: '',
        });
      });

      readyRef.current = true;
      syncData();
    });

    return () => {
      focusMarkerRef.current?.remove();
      map.remove();
      mapRef.current = null;
      readyRef.current = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function syncData() {
    const map = mapRef.current;
    if (!map || !readyRef.current) return;
    const highlighted = new Set(highlightedCameraIds);
    const camSrc = map.getSource('cameras') as maplibregl.GeoJSONSource | undefined;
    camSrc?.setData(cameraFeatureCollection(cameras, highlighted) as GeoJSONFeatureCollection);

    const trajSrc = map.getSource('trajectories') as maplibregl.GeoJSONSource | undefined;
    trajSrc?.setData(trajectoryFeatureCollection(trajectories) as GeoJSONFeatureCollection);
  }

  // Keep sources in sync with props.
  useEffect(() => {
    syncData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [cameras, trajectories, highlightedCameraIds]);

  // Fly to / fit bounds around the selected vehicle's trajectory. This must
  // re-run once the trajectory data actually arrives, not just when the
  // vehicle id changes — trajectories load asynchronously after selection,
  // so depending on selectedVehicleId alone fires this while `trajectories`
  // is still the previous (or empty) value and never runs again once the
  // real route lands.
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !readyRef.current || !selectedVehicleId) return;
    if (trajectories.length === 0) return;
    // trajectories.data isn't cleared while a new fetch is in flight, so
    // right after switching vehicles this can still be the *previous*
    // vehicle's route for one render. Ignore it until the fetch resolves
    // and the data actually matches the currently selected vehicle.
    if (trajectories.some((t) => t.vehicle_id !== selectedVehicleId)) return;

    const coords: [number, number][] = [];
    for (const traj of trajectories) {
      for (const seg of traj.route_geometry ?? []) {
        for (const p of seg.points ?? []) coords.push([p.lon, p.lat]);
      }
      for (const o of traj.observations) {
        const cam = cameras.find((c) => c.camera_id === o.camera_id);
        if (cam) coords.push([cam.longitude, cam.latitude]);
      }
    }

    if (coords.length === 0) {
      // No route geometry or matched observations at all — fall back to
      // the vehicle's single most recent observation so we still move the
      // camera to "where the vehicle is" rather than doing nothing.
      const fallback = latestObservationCoord(trajectories, cameras);
      if (fallback) map.flyTo({ center: fallback, zoom: 15, duration: 900 });
      return;
    }
    if (coords.length === 1) {
      map.flyTo({ center: coords[0], zoom: 15, duration: 900 });
      return;
    }
    const bounds = coords.reduce(
      (b, c) => b.extend(c),
      new maplibregl.LngLatBounds(coords[0], coords[0]),
    );
    map.fitBounds(bounds, { padding: 90, duration: 900, maxZoom: 16 });
  }, [selectedVehicleId, trajectories, cameras]);

  // Larger pulsing ring marker over the selected vehicle's current (most
  // recent) camera — distinct from the amber alert-range highlight, which
  // can mark several cameras at once for an unrelated reason.
  useEffect(() => {
    focusMarkerRef.current?.remove();
    focusMarkerRef.current = null;
    const map = mapRef.current;
    if (!map || !focusedCameraId) return;
    const cam = cameras.find((c) => c.camera_id === focusedCameraId);
    if (!cam) return;

    const el = document.createElement('div');
    el.style.width = '26px';
    el.style.height = '26px';
    el.style.display = 'flex';
    el.style.alignItems = 'center';
    el.style.justifyContent = 'center';
    el.innerHTML =
      '<span class="absolute inline-flex h-5 w-5 rounded-full animate-pulse-live" style="background-color:var(--color-accent)"></span>' +
      '<span class="relative inline-flex h-3 w-3 rounded-full border-2" style="background-color:var(--color-accent);border-color:var(--color-ink);box-shadow:0 0 14px 2px var(--color-accent)"></span>';

    focusMarkerRef.current = new maplibregl.Marker({ element: el, anchor: 'center' })
      .setLngLat([cam.longitude, cam.latitude])
      .addTo(map);
  }, [focusedCameraId, cameras]);

  // Explicit camera selection (Cameras tab, map click, or the camera
  // filter) pans/zooms the map independently of any vehicle trajectory fit.
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !readyRef.current || !flyToCameraId) return;
    const cam = cameras.find((c) => c.camera_id === flyToCameraId);
    if (!cam) return;
    map.flyTo({ center: [cam.longitude, cam.latitude], zoom: 16, duration: 800 });
  }, [flyToCameraId, cameras]);

  return (
    <div className="absolute inset-0 h-full w-full">
      <div ref={containerRef} className="absolute inset-0 h-full w-full" />
      {mapError && (
        <div className="absolute inset-0 flex items-center justify-center bg-ink px-6 text-center">
          <div className="max-w-sm space-y-2">
            <div className="h-8 w-8 mx-auto rounded-full bg-severity-high/15 flex items-center justify-center text-severity-high">
              !
            </div>
            <p className="text-sm font-medium text-fg">Map failed to load</p>
            <p className="text-xs text-fg-muted">{mapError}</p>
            <p className="text-[11px] text-fg-faint">
              This usually means the browser or device doesn't support WebGL2, or the basemap
              host is unreachable. Camera, alert, and live-feed data above are unaffected.
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
