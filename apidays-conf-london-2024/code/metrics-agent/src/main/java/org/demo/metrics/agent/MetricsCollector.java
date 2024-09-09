package org.demo.metrics.agent;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;
import org.springframework.web.client.RestClient;

@Component
public class MetricsCollector {
    private static final Logger LOGGER = LoggerFactory.getLogger(MetricsCollector.class);
    private final RestClient restClient;
    private final MetricsPublisher publisher;

    public MetricsCollector(RestClient restClient, MetricsPublisher publisher) {
        this.restClient = restClient;
        this.publisher = publisher;
    }

    @Scheduled(fixedRate = 5000)
    public void collectMetrics() {
       MetricsData metricsData = restClient.get().retrieve().body(MetricsData.class);

       LOGGER.info("Metrics data collected: {}", metricsData);

       publisher.publishMetrics(metricsData);

        LOGGER.info("Metrics data published");
    }

}
