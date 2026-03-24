package com.aipass;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.scheduling.annotation.EnableScheduling;

@EnableScheduling
@SpringBootApplication
public class AipassApplication {

	public static void main(String[] args) {
		SpringApplication.run(AipassApplication.class, args);
	}

}
