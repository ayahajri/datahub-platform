package com.datahub.repository;

import com.datahub.entity.Data;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;



public interface DataRepository extends JpaRepository<Data, Long> {

    List<Data> findByCreatedBy(String createdBy);

    List<Data> findByCreatedByAndTitleContainingIgnoreCase(String createdBy, String title);

    Page<Data> findByCreatedBy(String createdBy, Pageable pageable);
}