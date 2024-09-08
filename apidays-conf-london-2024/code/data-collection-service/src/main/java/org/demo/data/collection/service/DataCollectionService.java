package org.demo.data.collection.service;

import com.fasterxml.jackson.databind.ObjectMapper;
import io.cloudevents.CloudEvent;
import io.cloudevents.core.format.EventFormat;
import io.nats.client.ConsumerContext;
import io.nats.client.Message;
import io.nats.client.MessageConsumer;
import jakarta.annotation.PostConstruct;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;

import java.io.IOException;
import java.util.List;
import java.util.concurrent.CopyOnWriteArrayList;

@Service
public class DataCollectionService {

    private static final Logger LOGGER = LoggerFactory.getLogger(DataCollectionService.class);
    private final ConsumerContext consumerContext;
    private final EventFormat eventFormat;
    private final ObjectMapper mapper;

    private final List<MetricsData> metricsList = new CopyOnWriteArrayList<>();

    public DataCollectionService(
            ConsumerContext consumerContext,
            EventFormat eventFormat,
            ObjectMapper mapper
    ) {
        this.consumerContext = consumerContext;
        this.eventFormat = eventFormat;
        this.mapper = mapper;
    }

    public List<MetricsData> getAllCollectedMetrics() {
        // We use an in-memory list to store the metrics data
        // This is just for demonstration purposes
        // In a real-world scenario, you would store this data in a database
        return metricsList;
    }

    @PostConstruct
    public void init() {
        try (MessageConsumer consumer = consumerContext.consume(this::processMessage)) {
            LOGGER.info("Listening for messages");
        } catch (Exception e) {
            LOGGER.error("Failed to consume messages", e);

            throw new RuntimeException("Failed to consume messages from NATS", e);
        }
    }

    private void processMessage(Message message) {
        LOGGER.info("Received message: {}", message);
        message.ack();

        byte[] data = message.getData();
        CloudEvent cloudEvent = fromCloudEventBytes(data);
        MetricsData metricsData = fromMetricsDataBytes(cloudEvent.getData().toBytes());

        metricsList.add(metricsData);
    }

    private CloudEvent fromCloudEventBytes(byte[] data) {
        return eventFormat.deserialize(data);
    }

    private MetricsData fromMetricsDataBytes(byte[] data) {
        try {
            return mapper.readValue(data, MetricsData.class);
        } catch (IOException e) {
            throw new RuntimeException("Could not deserialize metrics data", e);
        }
    }
}
