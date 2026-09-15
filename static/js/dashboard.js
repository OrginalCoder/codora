function renderAnalyticsChart(containerId, labels, dataPoints, title) {
  const container = document.getElementById(containerId);
  if (!container || !dataPoints.length) return;

  const maxVal = Math.max(...dataPoints, 10);
  const height = 220;
  const width = container.clientWidth || 600;
  const padding = 35;
  const graphWidth = width - (padding * 2);
  const graphHeight = height - (padding * 2);

  const stepX = dataPoints.length > 1 ? graphWidth / (dataPoints.length - 1) : graphWidth;

  const points = dataPoints.map((val, idx) => {
    const x = padding + (idx * stepX);
    const y = height - padding - ((val / maxVal) * graphHeight);
    return `${x},${y}`;
  }).join(' ');

  let dotsHtml = '';
  dataPoints.forEach((val, idx) => {
    const x = padding + (idx * stepX);
    const y = height - padding - ((val / maxVal) * graphHeight);
    const label = labels[idx] || '';
    dotsHtml += `
      <circle cx="${x}" cy="${y}" r="4" fill="#3b82f6" stroke="#ffffff" stroke-width="2" />
      <text x="${x}" y="${height - 10}" text-anchor="middle" font-size="11" fill="#8493a8">${label}</text>
      <text x="${x}" y="${y - 10}" text-anchor="middle" font-size="11" font-weight="600" fill="#f8fafc">${val}</text>
    `;
  });

  const svgHtml = `
    <svg width="100%" height="${height}" viewBox="0 0 ${width} ${height}" style="overflow: visible;">
      <defs>
        <linearGradient id="chartGrad" x1="0%" y1="0%" x2="0%" y2="100%">
          <stop offset="0%" stop-color="#3b82f6" stop-opacity="0.25" />
          <stop offset="100%" stop-color="#3b82f6" stop-opacity="0.0" />
        </linearGradient>
      </defs>
      <line x1="${padding}" y1="${height - padding}" x2="${width - padding}" y2="${height - padding}" stroke="#22304d" stroke-width="1" />
      <polygon points="${padding},${height - padding} ${points} ${width - padding},${height - padding}" fill="url(#chartGrad)" />
      <polyline points="${points}" fill="none" stroke="#3b82f6" stroke-width="3" stroke-linecap="round" stroke-linejoin="round" />
      ${dotsHtml}
    </svg>
  `;

  container.innerHTML = svgHtml;
}

document.addEventListener('DOMContentLoaded', function() {
  const thumbInput = document.getElementById('id_thumbnail');
  const thumbPreview = document.getElementById('thumbnail-preview');
  if (thumbInput && thumbPreview) {
    thumbInput.addEventListener('change', function() {
      const file = this.files[0];
      if (file) {
        const reader = new FileReader();
        reader.onload = function(e) {
          thumbPreview.src = e.target.result;
          thumbPreview.style.display = 'block';
        };
        reader.readAsDataURL(file);
      }
    });
  }
});
