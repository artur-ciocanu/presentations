package com.example.hub.repository;

import com.example.hub.model.AgentConfig;
import org.springframework.data.mongodb.repository.MongoRepository;

import java.util.Optional;

public interface AgentConfigRepository extends MongoRepository<AgentConfig, String> {
    Optional<AgentConfig> findByAgentId(String agentId);
    boolean existsByAgentId(String agentId);
}
