package com.datahub.controller;

import com.datahub.entity.AnalysisJob;
import com.datahub.service.AnalysisService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.Authentication;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.server.ResponseStatusException;

import java.io.IOException;

/**
 * Downloads the full report of an analysis the platform already ran:
 *   GET /api/analysis/{id}/export/pdf
 *   GET /api/analysis/{id}/export/csv?type=stats|quality|outliers|clusters
 *
 * If Spring fails at startup with "Ambiguous mapping", an endpoint with the same path
 * already exists in AnalysisController: delete the old one there.
 */
@RestController
@RequestMapping("/api/analysis")
public class ExportController {

    @Autowired
    private AnalysisService analysisService;

    @GetMapping("/{id}/export/pdf")
    public ResponseEntity<byte[]> exportPdf(@PathVariable Long id,
                                            @RequestParam(required = false) String title,
                                            Authentication authentication) {
        // authentication.getName() must be the user's email (same value stored in AnalysisJob.userEmail)
        AnalysisJob job = analysisService.getJobForUser(id, authentication.getName());
        try {
            byte[] pdf = (title == null || title.isBlank())
                    ? analysisService.generatePDF(job)
                    : analysisService.generatePDF(job, title);

            return ResponseEntity.ok()
                    .contentType(MediaType.APPLICATION_PDF)
                    .header(HttpHeaders.CONTENT_DISPOSITION, "attachment; filename=\"report_" + id + ".pdf\"")
                    .body(pdf);
        } catch (IOException e) {
            throw new ResponseStatusException(HttpStatus.BAD_GATEWAY, e.getMessage());
        }
    }

    @GetMapping("/{id}/export/csv")
    public ResponseEntity<byte[]> exportCsv(@PathVariable Long id,
                                            @RequestParam(defaultValue = "stats") String type,
                                            Authentication authentication) {
        AnalysisJob job = analysisService.getJobForUser(id, authentication.getName());
        try {
            byte[] csv = analysisService.generateCSV(job, type);

            return ResponseEntity.ok()
                    .contentType(MediaType.parseMediaType("text/csv"))
                    .header(HttpHeaders.CONTENT_DISPOSITION,
                            "attachment; filename=\"" + type + "_" + id + ".csv\"")
                    .body(csv);
        } catch (IOException e) {
            throw new ResponseStatusException(HttpStatus.BAD_GATEWAY, e.getMessage());
        }
    }
}