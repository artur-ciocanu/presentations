package org.demo.app;

import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;

import java.time.Instant;
import java.util.concurrent.ThreadLocalRandom;

@RestController
public class MetricsDataController {

    @GetMapping("/metrics")
    public MetricsData getMetricsData() {
        ThreadLocalRandom random = ThreadLocalRandom.current();
        MetricsData result = new MetricsData();

        result.setCpuUsage(random.nextInt(20, 85));
        result.setMemoryUsage(random.nextInt(2048, 4096));
        result.setHttpRequestCount(random.nextInt(300, 1000));
        result.setTimestamp(Instant.now().toEpochMilli());

        return result;
    }
}
