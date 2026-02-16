package com.example.hub.model;

import jakarta.validation.constraints.*;
import lombok.*;
import org.springframework.data.annotation.Id;
import org.springframework.data.annotation.Version;
import org.springframework.data.mongodb.core.index.Indexed;
import org.springframework.data.mongodb.core.mapping.Document;

import java.time.Instant;
import java.util.List;
import java.util.Map;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
@Document(collection = "agentConfigs")
public class AgentConfig {

    @Id
    private String id;

    @NotBlank
    @Pattern(regexp = "^[a-z0-9-]+$")
    @Indexed(unique = true)
    private String agentId;

    @NotBlank
    @Size(min = 1, max = 100)
    private String name;

    @NotNull
    private ModelProvider modelProvider;

    @NotBlank
    private String modelId;

    @NotNull
    @DecimalMin("0.0")
    @DecimalMax("2.0")
    private Double temperature;

    @Min(1)
    @Max(128000)
    private Integer maxTokens;

    private String systemPrompt;

    private List<String> tools;

    private Map<String, Object> metadata;

    @Version
    private Integer version;

    private Instant updatedAt;

    public enum ModelProvider {
        OPENAI, ANTHROPIC, GOOGLE, MISTRAL
    }
}
