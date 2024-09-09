package org.demo.metrics.agent;

public record MetricsData(int cpuUsage, int memoryUsage, int httpRequestCount, long timestamp) {}
