package org.demo.reporting.service;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import io.cloudevents.CloudEvent;
import io.cloudevents.core.format.EventFormat;
import io.nats.client.Connection;
import io.nats.client.Message;
import jakarta.annotation.PostConstruct;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;

import java.io.IOException;
import java.time.Duration;
import java.util.List;

@Service
public class ReportingService {

    private static final Logger LOGGER = LoggerFactory.getLogger(ReportingService.class);

    private static final TypeReference<List<MetricsData>> METRICS_LIST_TYPE = new TypeReference<>() {};

    private final Connection natsConnection;
    private final EventFormat eventFormat;
    private final ObjectMapper mapper;

    public ReportingService(Connection natsConnection, EventFormat eventFormat, ObjectMapper mapper) {
        this.natsConnection = natsConnection;
        this.eventFormat = eventFormat;
        this.mapper = mapper;
    }

    public List<MetricsData> getAllMetrics() {
        try {
            Message message = natsConnection.request("get-metrics", null, Duration.ofSeconds(10));

            LOGGER.info("Received message: {}", message);

            return getAllMetrics(message);
        } catch (InterruptedException e) {
            LOGGER.error("Can not retrieve metrics", e);

            throw new RuntimeException("Can not retrieve metrics", e);
        }
    }

    private List<MetricsData> getAllMetrics(Message message) {
        byte[] data = message.getData();
        CloudEvent cloudEvent = fromCloudEventBytes(data);

        return fromMetricsDataBytes(cloudEvent.getData().toBytes());
    }

    private CloudEvent fromCloudEventBytes(byte[] data) {
        return eventFormat.deserialize(data);
    }

    private List<MetricsData> fromMetricsDataBytes(byte[] data) {
        try {
            return mapper.readValue(data, METRICS_LIST_TYPE);
        } catch (IOException e) {
            throw new RuntimeException("Could not deserialize metrics data", e);
        }
    }
}
