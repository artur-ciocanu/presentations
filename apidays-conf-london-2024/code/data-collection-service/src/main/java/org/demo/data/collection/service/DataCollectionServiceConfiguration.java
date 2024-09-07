package org.demo.data.collection.service;

import io.cloudevents.core.provider.EventFormatProvider;
import io.nats.client.*;
import io.nats.client.api.AckPolicy;
import io.nats.client.api.ConsumerConfiguration;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

import java.io.IOException;

@Configuration
public class DataCollectionServiceConfiguration {

    private static final String NATS_URL = "nats://localhost:4222";
    private static final String STREAM_NAME = "METRICS";

    @Bean
    public Connection connection() throws IOException, InterruptedException {
        return Nats.connect(NATS_URL);
    }

    @Bean
    public JetStream jetStream(Connection natsConnection) throws IOException {
        return natsConnection.jetStream();
    }

    @Bean
    public ConsumerContext consumerContext(JetStream jetStream) throws IOException, JetStreamApiException {
        StreamContext streamContext = jetStream.getStreamContext(STREAM_NAME);
        ConsumerConfiguration consumerConfiguration = ConsumerConfiguration
                .builder()
                .ackPolicy(AckPolicy.Explicit)
                .maxAckPending(1)
                .build();

        return streamContext.createOrUpdateConsumer(consumerConfiguration);
    }

    @Bean
    public EventFormatProvider eventFormatProvider() {
        return EventFormatProvider.getInstance();
    }
}
