package org.demo.metrics.agent;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import io.cloudevents.CloudEvent;
import io.cloudevents.core.format.ContentType;
import io.cloudevents.core.provider.EventFormatProvider;
import io.cloudevents.core.v1.CloudEventBuilder;
import io.nats.client.JetStream;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Component;

import java.net.URI;
import java.util.UUID;

@Component
public class MetricsPublisher {

    private static final Logger LOGGER = LoggerFactory.getLogger(MetricsCollector.class);

    // TODO: This should be read from a configuration file
    // But for the sake of simplicity, we are hard coding it here
    private static final String SUBJECT = "metrics.us-east-1";
    private static final String TYPE = "metric";

    private final ObjectMapper mapper;
    private final EventFormatProvider eventFormatProvider;
    private final JetStream jetStream;

    public MetricsPublisher(ObjectMapper mapper, EventFormatProvider eventFormatProvider, JetStream jetStream) {
        this.mapper = mapper;
        this.eventFormatProvider = eventFormatProvider;
        this.jetStream = jetStream;
    }

    public void publishMetrics(MetricsData data) {
        CloudEvent cloudEvent = toCloudEvent(data);

        publishCloudEvent(cloudEvent);
    }

    private void publishCloudEvent(CloudEvent cloudEvent) {
        byte[] payload = serialize(cloudEvent);

        try {
            jetStream.publish(SUBJECT, payload);
        } catch (Exception e) {
            LOGGER.error("Failed to publish metrics", e);

            throw new RuntimeException("Failed to publish metrics", e);
        }
    }

    private CloudEvent toCloudEvent(MetricsData data) {
        byte[] dataBytes = serialize(data);

        return new CloudEventBuilder()
            .withId(UUID.randomUUID().toString())
            .withSubject(SUBJECT)
            .withType(TYPE)
            .withSource(URI.create("https://observability.acme.com/metrics"))
            .withData(dataBytes)
            .build();
    }

    private byte[] serialize(CloudEvent cloudEvent) {
        return eventFormatProvider
            .resolveFormat(ContentType.JSON)
            .serialize(cloudEvent);
    }

    private byte[] serialize(MetricsData data) {
        try {
            return mapper.writeValueAsBytes(data);
        } catch (JsonProcessingException e) {
            LOGGER.error("Failed to serialize metrics data", e);

            throw new RuntimeException("Failed to serialize metrics data", e);
        }
    }
}
