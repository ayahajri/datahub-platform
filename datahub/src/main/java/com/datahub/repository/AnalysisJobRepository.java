package com.datahub.repository;

import com.datahub.entity.AnalysisJob;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;

@Repository
public interface AnalysisJobRepository extends JpaRepository<AnalysisJob, Long> {

    List<AnalysisJob> findByUserEmailOrderByCreatedAtDesc(String userEmail);
}