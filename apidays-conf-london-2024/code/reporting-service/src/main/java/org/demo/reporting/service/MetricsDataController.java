package org.demo.reporting.service;

import org.springframework.web.bind.annotation.CrossOrigin;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;

@RestController
public class MetricsDataController {

    private final ReportingService reportingService;

    public MetricsDataController(ReportingService reportingService) {
        this.reportingService = reportingService;
    }

    @GetMapping("/metrics")
    @CrossOrigin(origins = "http://localhost:9090")
    public List<MetricsData> getAllMetrics() {
        return reportingService.getAllMetrics();
    }
}
