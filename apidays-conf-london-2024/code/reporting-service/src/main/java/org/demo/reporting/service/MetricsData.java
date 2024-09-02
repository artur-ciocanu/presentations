package org.demo.reporting.service;

public class MetricsData {

    private final int cpuUsage;
    private final int memoryUsage;
    private final int httpRequestCount;

    public MetricsData(int cpuUsage, int memoryUsage, int httpRequestCount) {
        this.cpuUsage = cpuUsage;
        this.memoryUsage = memoryUsage;
        this.httpRequestCount = httpRequestCount;
    }

    public int getCpuUsage() {
        return cpuUsage;
    }

    public int getMemoryUsage() {
        return memoryUsage;
    }

    public int getHttpRequestCount() {
        return httpRequestCount;
    }
}
