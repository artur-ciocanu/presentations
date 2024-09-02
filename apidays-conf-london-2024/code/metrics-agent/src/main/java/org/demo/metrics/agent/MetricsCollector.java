package org.demo.metrics.agent;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;

@Component
public class MetricsCollector {

    private static final Logger LOGGER = LoggerFactory.getLogger(MetricsCollector.class);

    @Scheduled(fixedRate = 2000)
    public void collectMetrics() {
        LOGGER.info("Collecting metrics...");
        // TODO: Add logic to get metrics from app and publish to NATS
    }
}
