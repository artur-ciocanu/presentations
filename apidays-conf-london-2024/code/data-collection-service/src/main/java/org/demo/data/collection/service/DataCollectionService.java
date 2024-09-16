package org.demo.data.collection.service;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import io.cloudevents.CloudEvent;
import io.cloudevents.core.format.EventFormat;
import io.cloudevents.core.v1.CloudEventBuilder;
import io.nats.client.*;
import jakarta.annotation.PostConstruct;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;

import java.io.IOException;
import java.net.URI;
import java.util.List;
import java.util.UUID;
import java.util.concurrent.CopyOnWriteArrayList;

@Service
public class DataCollectionService {
    private static final Logger LOGGER = LoggerFactory.getLogger(DataCollectionService.class);

    private static final String TYPE = "metrics";
    private static final String SUBJECT = "metrics.>";

    private final Connection natsConnection;
    private final ConsumerContext natsConsumer;
    private final EventFormat eventFormat;
    private final ObjectMapper mapper;

    private final List<MetricsData> metricsList = new CopyOnWriteArrayList<>();

    public DataCollectionService(
            Connection natsConnection,
            ConsumerContext natsConsumer,
            EventFormat eventFormat,
            ObjectMapper mapper
    ) {
        this.natsConnection = natsConnection;
        this.natsConsumer = natsConsumer;
        this.eventFormat = eventFormat;
        this.mapper = mapper;
    }

    @PostConstruct
    public void init() throws JetStreamApiException, IOException {
        natsConsumer.consume(this::processMessage);

        Dispatcher natsDispatcher = natsConnection.createDispatcher(this::publishAllMetrics);
        natsDispatcher.subscribe("get-metrics");
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

    private void publishAllMetrics(Message message) {
        CloudEvent cloudEvent = toCloudEvent(metricsList);
        byte[] payload = serialize(cloudEvent);

        natsConnection.publish(message.getReplyTo(), payload);
    }

    private CloudEvent toCloudEvent(List<MetricsData> metrics) {
        byte[] dataBytes = serializeMetricsList(metrics);

        return new CloudEventBuilder()
                .withId(UUID.randomUUID().toString())
                .withSubject(SUBJECT)
                .withType(TYPE)
                .withSource(URI.create("https://observability.acme.com/metrics"))
                .withData(dataBytes)
                .build();
    }

    private byte[] serializeMetricsList(List<MetricsData> metrics) {
        try {
            return mapper.writeValueAsBytes(metrics);
        } catch (JsonProcessingException e) {
            throw new RuntimeException("Can not serializer metrics list", e);
        }
    }

    private byte[] serialize(CloudEvent cloudEvent) {
        return eventFormat.serialize(cloudEvent);
    }
}
