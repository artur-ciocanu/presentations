package org.demo.reporting.service;

import io.cloudevents.core.format.ContentType;
import io.cloudevents.core.format.EventFormat;
import io.cloudevents.core.provider.EventFormatProvider;
import io.nats.client.Connection;
import io.nats.client.Nats;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

import java.io.IOException;

@Configuration
public class ReportingServiceConfiguration {

    private static final String NATS_URL = "nats://localhost:4222";

    @Bean
    public Connection connection() throws IOException, InterruptedException {
        return Nats.connect(NATS_URL);
    }

    @Bean
    public EventFormat eventFormat() {
        return EventFormatProvider.getInstance().resolveFormat(ContentType.JSON);
    }
}
