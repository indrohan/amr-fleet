/**
 * twin-bridge.js  v2
 *
 * Bridges amr-fleet WebSocket snapshots → DigitalTwin (Three.js).
 *
 * amr-fleet snapshot:
 *   { tick, mode,
 *     robots: [{id, pos:[row,col], state, battery, task_id, tasks_done,
 *               distance, path_remaining, heading_pickup}],
 *     warehouse: {rows, cols, grid, charging_stations, pickup_points, dropoff_points},
 *     tasks: [...], stats: {...}, events: [...] }
 *
 *   Robot states (uppercase strings):
 *     IDLE | NAVIGATING | PICKING_UP | DROPPING_OFF | CHARGING | WAITING | ERROR
 *
 * DigitalTwin.load({ map, meta, frames })
 *   map  : { width, height, grid[y][x], stations[[x,y]], docks[[x,y]] }
 *   meta : { cell_m, tasks_catalog[], dead_zones[] }
 *
 * DigitalTwin.update(frame, selectedId, cameraMode, simTime)
 *   frame: { robots:[{id,x,y,th,carry}],
 *            fleet: [{id,state,task,carry,path,peers,done,failed}],
 *            humans:[], obstacles:[] }
 */

import { DigitalTwin } from './digital-twin.js';

// ── Constants ─────────────────────────────────────────────────────────────────

const CELL_M = 1.5;   // metres per grid cell — makes warehouse fill the screen nicely

// ── Map conversion ────────────────────────────────────────────────────────────

/**
 * amr-fleet grid cell values → DigitalTwin cell values
 *   amr-fleet: 0=FREE  1=OBSTACLE  2=CHARGING  3=PICKUP  4=DROPOFF
 *   twin:      0=FREE  1=RACK      2=STATION   3=DOCK
 */
const GRID_REMAP = { 0: 0, 1: 1, 2: 3, 3: 2, 4: 2 };

function warehouseToMap(wh) {
  const rows = wh.rows;
  const cols = wh.cols;

  // twin grid is grid[y][x] where y=row, x=col — same layout as amr-fleet
  const grid = wh.grid.map(row => row.map(v => GRID_REMAP[v] ?? 0));

  // stations: pick + drop points → [x, y] == [col, row]
  const stations = [
    ...(wh.pickup_points  || []).map(([r, c]) => [c, r]),
    ...(wh.dropoff_points || []).map(([r, c]) => [c, r]),
  ];

  // docks: charging stations → [x, y]
  const docks = (wh.charging_stations || []).map(([r, c]) => [c, r]);

  return {
    width:  cols,
    height: rows,
    grid,
    stations,
    docks,
    pedestrian_apron: false,
  };
}

function buildMeta(wh) {
  return {
    cell_m:        CELL_M,
    tasks_catalog: [],
    dead_zones:    [],
  };
}

// ── Heading estimation ────────────────────────────────────────────────────────

// Estimate robot heading from position change between frames.
// Falls back to 0 (facing +X) when no movement.
const _prevPos = new Map();   // robotId → {row, col}

function estimateHeading(rid, row, col) {
  const prev = _prevPos.get(rid);
  _prevPos.set(rid, { row, col });
  if (!prev) return 0;
  const dr = row - prev.row;   // +row = south  (+Z in world)
  const dc = col - prev.col;   // +col = east   (+X in world)
  if (dr === 0 && dc === 0) return _prevPos.get(rid)._th ?? 0;
  // maths convention: angle from +X axis, CCW positive
  const th = Math.atan2(-dr, dc);   // -dr because world Z = -south
  _prevPos.get(rid)._th = th;
  return th;
}

// ── State mapping ─────────────────────────────────────────────────────────────

const STATE_MAP = {
  IDLE:         'idle',
  NAVIGATING:   'moving',
  PICKING_UP:   'moving',
  DROPPING_OFF: 'moving',
  CHARGING:     'charging',
  WAITING:      'blocked',
  ERROR:        'blocked',
};

// ── Frame conversion ──────────────────────────────────────────────────────────

function snapshotToFrame(snapshot) {
  const tick = snapshot.tick || 0;
  const simTime = tick * 0.1;

  const robots = (snapshot.robots || []).map(r => {
    const [row, col] = r.pos || [0, 0];
    const rid = robotId(r.id);
    const th  = estimateHeading(rid, row, col);
    const carrying = r.state === 'DROPPING_OFF' ||
                     (r.state === 'NAVIGATING' && r.heading_pickup === false);
    return {
      id:    rid,
      x:     col * CELL_M,   // east → +X
      y:     row * CELL_M,   // south → +Y (twin's depth axis)
      th,
      carry: carrying,
    };
  });

  const fleet = (snapshot.robots || []).map(r => {
    const rid = robotId(r.id);
    const carrying = r.state === 'DROPPING_OFF' ||
                     (r.state === 'NAVIGATING' && r.heading_pickup === false);
    return {
      id:     rid,
      state:  STATE_MAP[r.state] || 'idle',
      task:   r.task_id != null ? String(r.task_id) : null,
      carry:  carrying,
      path:   [],       // amr-fleet doesn't expose path cells in snapshot
      peers:  [],
      done:   r.tasks_done || 0,
      failed: r.state === 'ERROR',
    };
  });

  return {
    t:         simTime,
    robots,
    fleet,
    humans:    [],
    obstacles: [],
  };
}

function robotId(numericId) {
  return `AMR${String(numericId + 1).padStart(2, '0')}`;
}

// ── TwinBridge ────────────────────────────────────────────────────────────────

export class TwinBridge {
  /**
   * @param {HTMLCanvasElement} canvas
   * @param {Function}          onSelect  called with numeric robot id when clicked
   */
  constructor(canvas, onSelect) {
    this.twin       = new DigitalTwin(canvas, id => {
      // id is "AMR01" etc. — convert back to 0-based numeric
      if (onSelect) onSelect(parseInt(id.replace(/\D/g, ''), 10) - 1);
    });
    this.loaded        = false;
    this.simTime       = 0;
    this.selectedId    = null;   // "AMR01" format
    this.cameraMode    = 'overview';
    this._lastSnapshot = null;
    this._animFrame    = null;
    this._loop();
  }

  /** Feed a parsed WebSocket snapshot. */
  ingest(snapshot) {
    this._lastSnapshot = snapshot;

    if (!this.loaded && snapshot.warehouse?.grid) {
      const map  = warehouseToMap(snapshot.warehouse);
      const meta = buildMeta(snapshot.warehouse);
      const frame = snapshotToFrame(snapshot);

      this.twin.load({ map, meta, frames: [frame] });
      this.loaded = true;
    }
  }

  /** Select robot by 0-based numeric id (or null to deselect). */
  selectRobot(numericId) {
    this.selectedId = numericId != null ? robotId(numericId) : null;
  }

  setCameraMode(mode) {
    this.cameraMode = mode;
    if (this.twin) this.twin.setCameraMode(mode);
  }

  resize() {
    if (this.twin) this.twin.resize();
  }

  destroy() {
    if (this._animFrame) cancelAnimationFrame(this._animFrame);
    this._animFrame = null;
  }

  _loop() {
    this._animFrame = requestAnimationFrame(() => this._loop());
    if (!this.loaded || !this._lastSnapshot) return;

    const frame = snapshotToFrame(this._lastSnapshot);
    this.simTime = frame.t;
    this.twin.update(frame, this.selectedId, this.cameraMode, this.simTime);
  }
}
