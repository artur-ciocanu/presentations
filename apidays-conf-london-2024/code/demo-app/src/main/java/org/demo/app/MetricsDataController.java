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

        return new MetricsData(
                random.nextInt(20, 85),
                random.nextInt(2048, 4096),
                random.nextInt(300, 1000),
                Instant.now().toEpochMilli()
        );
    }
}
