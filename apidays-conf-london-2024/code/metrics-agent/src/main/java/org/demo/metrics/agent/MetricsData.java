package org.demo.metrics.agent;


public class MetricsData {
  private int cpuUsage;
  private int memoryUsage;
  private int httpRequestCount;
  private long timestamp;

  public int getCpuUsage() { return this.cpuUsage; }
  public void setCpuUsage(int cpuUsage) { this.cpuUsage = cpuUsage; }

  public int getMemoryUsage() { return this.memoryUsage; }
  public void setMemoryUsage(int memoryUsage) { this.memoryUsage = memoryUsage; }

  public int getHttpRequestCount() { return this.httpRequestCount; }
  public void setHttpRequestCount(int httpRequestCount) { this.httpRequestCount = httpRequestCount; }

  public long getTimestamp() { return this.timestamp; }
  public void setTimestamp(long timestamp) { this.timestamp = timestamp; }
}