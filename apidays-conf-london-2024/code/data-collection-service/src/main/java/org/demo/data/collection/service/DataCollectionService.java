package org.demo.data.collection.service;

import com.fasterxml.jackson.databind.ObjectMapper;
import io.cloudevents.CloudEvent;
import io.cloudevents.core.format.ContentType;
import io.cloudevents.core.provider.EventFormatProvider;
import io.nats.client.ConsumerContext;
import io.nats.client.JetStreamApiException;
import io.nats.client.Message;
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
    private final EventFormatProvider eventFormatProvider;
    private final ObjectMapper mapper;

    private final List<MetricsData> metricsList = new CopyOnWriteArrayList<>();

    public DataCollectionService(
            ConsumerContext consumerContext,
            EventFormatProvider eventFormatProvider,
            ObjectMapper mapper
    ) {
        this.consumerContext = consumerContext;
        this.eventFormatProvider = eventFormatProvider;
        this.mapper = mapper;
    }

    public List<MetricsData> getAllCollectedMetrics() {
        // We use an in-memory list to store the metrics data
        // This is just for demonstration purposes
        // In a real-world scenario, you would store this data in a database
        return metricsList;
    }

    @PostConstruct
    public void init() throws JetStreamApiException, IOException {
        consumerContext.consume(this::processMessage);
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
        return eventFormatProvider
                .resolveFormat(ContentType.JSON)
                .deserialize(data);
    }

    private MetricsData fromMetricsDataBytes(byte[] data) {
        try {
            return mapper.readValue(data, MetricsData.class);
        } catch (IOException e) {
            throw new RuntimeException("Could not deserialize metrics data", e);
        }
    }
}
