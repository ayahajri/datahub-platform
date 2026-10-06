package com.datahub.service;

import com.datahub.entity.AnalysisJob;
import com.datahub.repository.AnalysisJobRepository;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.core.io.ByteArrayResource;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.stereotype.Service;
import org.springframework.util.LinkedMultiValueMap;
import org.springframework.util.MultiValueMap;
import org.springframework.web.client.RestClient;
import org.springframework.web.client.RestClientResponseException;
import org.springframework.web.multipart.MultipartFile;
import org.springframework.web.server.ResponseStatusException;

import java.io.IOException;
import java.time.LocalDateTime;
import java.util.HashMap;
import java.util.Map;

@Service
public class AnalysisService {

    @Autowired
    private AnalysisJobRepository analysisJobRepository;

    @Autowired
    private RestClient restClient;

    @Value("${python.service.url:http://localhost:8000}")
    private String pythonServiceUrl;

    private final ObjectMapper objectMapper = new ObjectMapper();

    // ==================== UPLOAD & ANALYZE ====================

    public AnalysisJob uploadAndAnalyze(MultipartFile file, String analysisType, String userEmail) throws IOException {
        AnalysisJob job = new AnalysisJob();
        job.setUserEmail(userEmail);
        job.setOriginalFileName(file.getOriginalFilename());
        job.setFileType(getFileType(file.getOriginalFilename()));
        job.setAnalysisType(analysisType);
        job.setStatus("PENDING");
        job.setCreatedAt(LocalDateTime.now());

        job = analysisJobRepository.save(job);

        try {
            String response = postMultipart("/analyze", file,
                    Map.of("analysis_type", orDefault(analysisType, "STATS")));

            job.setResultJson(response);
            job.setStatus("DONE");
            job.setCompletedAt(LocalDateTime.now());
        } catch (Exception e) {
            job.setStatus("FAILED");
            job.setErrorMessage(e.getMessage());
            job.setCompletedAt(LocalDateTime.now());
        }

        return analysisJobRepository.save(job);
    }

    // ==================== DATA PREVIEW ====================

    @SuppressWarnings("unchecked")
    public Map<String, Object> previewData(MultipartFile file) throws IOException {
        try {
            String response = postMultipart("/preview", file, Map.of());
            return objectMapper.readValue(response, Map.class);
        } catch (Exception e) {
            throw new IOException("Error previewing data: " + e.getMessage());
        }
    }

    // ==================== QUALITY REPORT ====================

    @SuppressWarnings("unchecked")
    public Map<String, Object> qualityReport(MultipartFile file) throws IOException {
        try {
            String response = postMultipart("/quality-report", file, Map.of());
            return objectMapper.readValue(response, Map.class);
        } catch (Exception e) {
            throw new IOException("Error generating quality report: " + e.getMessage());
        }
    }

    // ==================== PDF / CSV EXPORT (from the saved analysis result) ====================

    /** Loads a job and checks it belongs to the user (use findById directly for admins). */
    public AnalysisJob getJobForUser(Long id, String userEmail) {
        AnalysisJob job = analysisJobRepository.findById(id)
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "Analysis not found"));
        if (userEmail == null || !userEmail.equals(job.getUserEmail())) {
            throw new ResponseStatusException(HttpStatus.FORBIDDEN, "This analysis is not yours");
        }
        return job;
    }

    public byte[] generatePDF(AnalysisJob job) throws IOException {
        return generatePDF(job, "Analysis Report - " + job.getOriginalFileName());
    }

    public byte[] generatePDF(AnalysisJob job, String title) throws IOException {
        return postJsonForBytes("/export-pdf", job,
                Map.of("title", orDefault(title, "Data Analysis Report")));
    }

    public byte[] generateCSV(AnalysisJob job, String exportType) throws IOException {
        return postJsonForBytes("/export-csv", job,
                Map.of("export_type", orDefault(exportType, "stats")));
    }

    // ==================== HELPERS ====================

    private String orDefault(String value, String fallback) {
        return (value == null || value.isBlank()) ? fallback : value;
    }

    private String getFileType(String filename) {
        if (filename == null) return "UNKNOWN";
        String f = filename.toLowerCase();
        if (f.endsWith(".csv")) return "CSV";
        if (f.endsWith(".xlsx") || f.endsWith(".xls")) return "EXCEL";
        if (f.endsWith(".json")) return "JSON";
        return "UNKNOWN";
    }

    private MultiValueMap<String, Object> buildBody(MultipartFile file, Map<String, String> fields) throws IOException {
        final String filename = file.getOriginalFilename();
        ByteArrayResource fileResource = new ByteArrayResource(file.getBytes()) {
            @Override
            public String getFilename() {
                return filename;
            }
        };
        MultiValueMap<String, Object> body = new LinkedMultiValueMap<>();
        body.add("file", fileResource);
        fields.forEach(body::add);
        return body;
    }

    private String postMultipart(String endpoint, MultipartFile file, Map<String, String> fields) throws IOException {
        try {
            return restClient.post()
                    .uri(pythonServiceUrl + endpoint)
                    .contentType(MediaType.MULTIPART_FORM_DATA)
                    .body(buildBody(file, fields))
                    .retrieve()
                    .body(String.class);
        } catch (RestClientResponseException e) {
            // Include Python's "detail" message so errors are readable
            throw new IOException(e.getStatusCode() + " from " + endpoint + ": " + e.getResponseBodyAsString());
        }
    }

    @SuppressWarnings("unchecked")
    private byte[] postJsonForBytes(String endpoint, AnalysisJob job, Map<String, String> extra) throws IOException {
        if (job.getResultJson() == null || job.getResultJson().isBlank()) {
            throw new IOException("This analysis has no result yet (status: " + job.getStatus() + ")");
        }
        Map<String, Object> body = new HashMap<>(extra);
        body.put("result", objectMapper.readValue(job.getResultJson(), Map.class));
        body.put("file_name", job.getOriginalFileName());

        try {
            return restClient.post()
                    .uri(pythonServiceUrl + endpoint)
                    .contentType(MediaType.APPLICATION_JSON)
                    .body(body)
                    .retrieve()
                    .body(byte[].class);
        } catch (RestClientResponseException e) {
            throw new IOException(e.getStatusCode() + " from " + endpoint + ": " + e.getResponseBodyAsString());
        } catch (Exception e) {
            throw new IOException("Error calling " + endpoint + ": " + e.getMessage());
        }
    }
}