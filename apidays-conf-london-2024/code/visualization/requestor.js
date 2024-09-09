function getMetricsData() {
  return fetch("http://localhost:8083/metrics")
    .then(response => response.json());
}
