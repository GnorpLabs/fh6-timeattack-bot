import { Chart, ChartConfiguration, registerables } from 'chart.js';
import { ColumnarLap } from '../../shared/types';

Chart.register(...registerables);

function makeLineChart(
  canvasId: string,
  label: string | string[],
  colors: string | string[],
  yLabel: string,
): Chart {
  const canvas = document.getElementById(canvasId) as HTMLCanvasElement;
  const labels_ = Array.isArray(label) ? label : [label];
  const colors_ = Array.isArray(colors) ? colors : [colors];

  const cfg: ChartConfiguration = {
    type: 'line',
    data: {
      labels: [],
      datasets: labels_.map((l, i) => ({
        label: l,
        data: [],
        borderColor: colors_[i],
        borderWidth: 1.5,
        pointRadius: 0,
        tension: 0,
      })),
    },
    options: {
      animation: false,
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { labels: { color: '#aaa', boxWidth: 12, font: { size: 11 } } },
      },
      scales: {
        x: { ticks: { color: '#666', maxTicksLimit: 10 }, grid: { color: '#222' } },
        y: {
          ticks: { color: '#aaa' },
          grid: { color: '#222' },
          title: { display: true, text: yLabel, color: '#666' },
        },
      },
    },
  };
  return new Chart(canvas, cfg);
}

export class ChartManager {
  private charts: Chart[] = [];

  isCreated(): boolean {
    return this.charts.length > 0;
  }

  createAll(): void {
    this.charts = [
      makeLineChart('chart-elevation', 'Elevation', '#4ecdc4', 'Y (m)'),
      makeLineChart('chart-speed', 'Speed', '#ffe66d', 'km/h'),
      makeLineChart(
        'chart-inputs',
        ['Throttle', 'Brake', 'Clutch', 'Handbrake', 'Steer'],
        ['#2ecc71', '#e74c3c', '#9b59b6', '#e67e22', '#3498db'],
        '0–255 / -127–127',
      ),
      makeLineChart('chart-gear', 'Gear', '#f39c12', 'Gear'),
      makeLineChart('chart-rpm', 'RPM', '#e74c3c', 'RPM'),
      makeLineChart('chart-boost', 'Boost', '#1abc9c', 'PSI'),
      makeLineChart(
        'chart-tire-temp',
        ['FL', 'FR', 'RL', 'RR'],
        ['#e74c3c', '#3498db', '#2ecc71', '#f39c12'],
        '°C',
      ),
      makeLineChart(
        'chart-tire-slip',
        ['FL', 'FR', 'RL', 'RR'],
        ['#e74c3c', '#3498db', '#2ecc71', '#f39c12'],
        'Slip',
      ),
      makeLineChart(
        'chart-suspension',
        ['FL', 'FR', 'RL', 'RR'],
        ['#e74c3c', '#3498db', '#2ecc71', '#f39c12'],
        'm',
      ),
    ];
  }

  load(col: ColumnarLap): void {
    const f = col.fields;
    const tLabels = f.t.map(t => t.toFixed(2));
    const speedKmh = f.speed.map(s => s * 3.6);

    const datasets: number[][][] = [
      [f.posY],
      [speedKmh],
      [f.throttle, f.brake, f.clutch, f.handbrake, f.steer],
      [f.gear],
      [f.rpm],
      [f.boost],
      [f.tireTempFL, f.tireTempFR, f.tireTempRL, f.tireTempRR],
      [f.tireSlipFL, f.tireSlipFR, f.tireSlipRL, f.tireSlipRR],
      [f.suspFL, f.suspFR, f.suspRL, f.suspRR],
    ];

    this.charts.forEach((chart, i) => {
      chart.data.labels = tLabels;
      const ds = datasets[i];
      chart.data.datasets.forEach((dataset, j) => {
        dataset.data = ds[j] ?? ds[0];
      });
      chart.update('none');
    });
  }

  setPlayhead(frameIndex: number): void {
    this.charts.forEach(chart => {
      const meta = chart.data.labels as string[];
      if (!meta || frameIndex >= meta.length) return;
      const xScale = (chart as unknown as { scales: Record<string, { getPixelForValue: (v: string) => number; top: number; bottom: number }> }).scales['x'];
      const yScale = (chart as unknown as { scales: Record<string, { top: number; bottom: number }> }).scales['y'];
      const xPos = xScale.getPixelForValue(meta[frameIndex]);
      const { top, bottom } = yScale;
      const ctx = chart.ctx;
      ctx.save();
      ctx.beginPath();
      ctx.strokeStyle = 'rgba(255,255,255,0.8)';
      ctx.lineWidth = 1;
      ctx.setLineDash([4, 3]);
      ctx.moveTo(xPos, top);
      ctx.lineTo(xPos, bottom);
      ctx.stroke();
      ctx.restore();
    });
  }

  redrawAll(): void {
    this.charts.forEach(c => c.draw());
  }

  destroy(): void {
    this.charts.forEach(c => c.destroy());
    this.charts = [];
  }
}
