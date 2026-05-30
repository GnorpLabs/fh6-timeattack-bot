export class TrackMap {
  private ctx: CanvasRenderingContext2D;
  private points: { x: number; z: number }[] = [];
  private minX = Infinity; private maxX = -Infinity;
  private minZ = Infinity; private maxZ = -Infinity;

  constructor(private readonly canvas: HTMLCanvasElement) {
    this.ctx = canvas.getContext('2d')!;
  }

  addPoint(posX: number, posZ: number): void {
    this.points.push({ x: posX, z: posZ });
    this.minX = Math.min(this.minX, posX);
    this.maxX = Math.max(this.maxX, posX);
    this.minZ = Math.min(this.minZ, posZ);
    this.maxZ = Math.max(this.maxZ, posZ);
  }

  loadPoints(posX: number[], posZ: number[]): void {
    this.points = posX.map((x, i) => ({ x, z: posZ[i] }));
    this.minX = Math.min(...posX);
    this.maxX = Math.max(...posX);
    this.minZ = Math.min(...posZ);
    this.maxZ = Math.max(...posZ);
  }

  reset(): void {
    this.points = [];
    this.minX = Infinity; this.maxX = -Infinity;
    this.minZ = Infinity; this.maxZ = -Infinity;
    this.clear();
  }

  private toCanvas(posX: number, posZ: number): { cx: number; cy: number } {
    const pad = 20;
    const rangeX = this.maxX - this.minX || 1;
    const rangeZ = this.maxZ - this.minZ || 1;
    const w = this.canvas.width - pad * 2;
    const h = this.canvas.height - pad * 2;
    return {
      cx: pad + ((posX - this.minX) / rangeX) * w,
      cy: pad + ((posZ - this.minZ) / rangeZ) * h,
    };
  }

  clear(): void {
    this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
  }

  drawLine(): void {
    if (this.points.length < 2) return;
    const ctx = this.ctx;
    ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
    ctx.beginPath();
    ctx.strokeStyle = '#3b9dff';
    ctx.lineWidth = 2;
    const first = this.toCanvas(this.points[0].x, this.points[0].z);
    ctx.moveTo(first.cx, first.cy);
    for (let i = 1; i < this.points.length; i++) {
      const { cx, cy } = this.toCanvas(this.points[i].x, this.points[i].z);
      ctx.lineTo(cx, cy);
    }
    ctx.stroke();
  }

  drawDotAtIndex(index: number): void {
    if (this.points.length === 0) return;
    const clamped = Math.max(0, Math.min(index, this.points.length - 1));
    const { cx, cy } = this.toCanvas(this.points[clamped].x, this.points[clamped].z);
    const ctx = this.ctx;
    ctx.beginPath();
    ctx.arc(cx, cy, 5, 0, Math.PI * 2);
    ctx.fillStyle = '#ff4444';
    ctx.fill();
  }

  drawDotAtLast(): void {
    this.drawDotAtIndex(this.points.length - 1);
  }
}
