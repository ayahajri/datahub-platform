package com.datahub.controller;

import com.datahub.entity.AnalysisJob;
import com.datahub.repository.AnalysisJobRepository;
import com.datahub.service.AnalysisService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.Authentication;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;
import org.springframework.web.server.ResponseStatusException;

import java.io.IOException;
import java.util.List;
import java.util.Map;

/**
 * Replaces the old AnalysisController. PDF/CSV export lives in ExportController.
 *   POST /api/analysis/upload   (file, analysisType)  -> AnalysisJob (with resultJson)
 *   POST /api/analysis/preview  (file)
 *   POST /api/analysis/quality  (file)
 *   GET  /api/analysis/history
 */
@RestController
@RequestMapping("/api/analysis")
public class AnalysisController {

    @Autowired
    private AnalysisService analysisService;

    @Autowired
    private AnalysisJobRepository analysisJobRepository;

    @PostMapping("/upload")
    public ResponseEntity<AnalysisJob> upload(@RequestParam("file") MultipartFile file,
                                              @RequestParam(value = "analysisType", defaultValue = "BOTH") String analysisType,
                                              Authentication authentication) throws IOException {
        // authentication.getName() = user's email
        return ResponseEntity.ok(analysisService.uploadAndAnalyze(file, analysisType, authentication.getName()));
    }

    @PostMapping("/preview")
    public ResponseEntity<Map<String, Object>> preview(@RequestParam("file") MultipartFile file) {
        try {
            return ResponseEntity.ok(analysisService.previewData(file));
        } catch (IOException e) {
            throw new ResponseStatusException(HttpStatus.BAD_GATEWAY, e.getMessage());
        }
    }

    @PostMapping({"/quality", "/quality-report"})
    public ResponseEntity<Map<String, Object>> quality(@RequestParam("file") MultipartFile file) {
        try {
            return ResponseEntity.ok(analysisService.qualityReport(file));
        } catch (IOException e) {
            throw new ResponseStatusException(HttpStatus.BAD_GATEWAY, e.getMessage());
        }
    }

    @GetMapping("/history")
    public ResponseEntity<List<AnalysisJob>> history(Authentication authentication) {
        return ResponseEntity.ok(
                analysisJobRepository.findByUserEmailOrderByCreatedAtDesc(authentication.getName()));
    }
}