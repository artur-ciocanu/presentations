package org.demo.data.collection.service;

import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;

@RestController
public class MetricsDataController {

    private final DataCollectionService dataCollectionService;

    public MetricsDataController(DataCollectionService dataCollectionService) {
        this.dataCollectionService = dataCollectionService;
    }

    @GetMapping("/metrics")
    public List<MetricsData> getMetricsData() {
        return dataCollectionService.getAllCollectedMetrics();
    }
}
