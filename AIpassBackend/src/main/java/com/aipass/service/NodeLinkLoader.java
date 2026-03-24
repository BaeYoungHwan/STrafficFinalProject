package com.aipass.service;

import jakarta.annotation.PostConstruct;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.core.io.ClassPathResource;
import org.springframework.stereotype.Component;

import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.nio.charset.StandardCharsets;
import java.util.HashMap;
import java.util.Map;

@Component
public class NodeLinkLoader {

    private static final Logger log = LoggerFactory.getLogger(NodeLinkLoader.class);

    private final Map<String, String[]> linkMap = new HashMap<>();
    private final Map<String, String> nodeMap = new HashMap<>();

    @PostConstruct
    public void load() {
        loadNodes();
        loadLinks();
        log.info("NodeLink 데이터 로딩 완료 — 노드: {}건, 링크: {}건", nodeMap.size(), linkMap.size());
    }

    private void loadNodes() {
        try {
            ClassPathResource resource = new ClassPathResource("data/ganghwa_nodes.csv");
            BufferedReader reader = new BufferedReader(
                    new InputStreamReader(resource.getInputStream(), StandardCharsets.UTF_8));

            String line = reader.readLine();
            while ((line = reader.readLine()) != null) {
                line = line.replace("\uFEFF", "");
                String[] cols = line.split(",", -1);
                if (cols.length >= 3) {
                    String nodeId = cols[0].trim();
                    String nodeName = cols[2].trim();
                    nodeMap.put(nodeId, nodeName);
                }
            }
            reader.close();
        } catch (Exception e) {
            log.error("ganghwa_nodes.csv 로딩 실패", e);
        }
    }

    private void loadLinks() {
        try {
            ClassPathResource resource = new ClassPathResource("data/ganghwa_links.csv");
            BufferedReader reader = new BufferedReader(
                    new InputStreamReader(resource.getInputStream(), StandardCharsets.UTF_8));

            String line = reader.readLine();
            while ((line = reader.readLine()) != null) {
                line = line.replace("\uFEFF", "");
                String[] cols = line.split(",", -1);
                if (cols.length >= 3) {
                    String linkId = cols[0].trim();
                    String fNode = cols[1].trim();
                    String tNode = cols[2].trim();
                    linkMap.put(linkId, new String[]{fNode, tNode});
                }
            }
            reader.close();
        } catch (Exception e) {
            log.error("ganghwa_links.csv 로딩 실패", e);
        }
    }

    public String[] getPointNames(String linkId) {
        String[] nodes = linkMap.get(linkId);
        if (nodes == null) {
            return null;
        }
        String startPoint = nodeMap.getOrDefault(nodes[0], nodes[0]);
        String endPoint = nodeMap.getOrDefault(nodes[1], nodes[1]);
        return new String[]{startPoint, endPoint};
    }

    public int getLinkCount() {
        return linkMap.size();
    }

    public int getNodeCount() {
        return nodeMap.size();
    }
}
