---
title: Medical Diagnosis System
emoji: 🏥
colorFrom: yellow
colorTo: green
sdk: docker
pinned: false
license: apache-2.0
short_description: University project creating an AI-powered medical system
python_version: 3.11
app_port: 7860
---

# Medical Diagnosis System

An AI-powered medical chatbot designed for patient-centric interactions, featuring persistent memory and a modern, intuitive user interface. This system is containerised using Docker for simplified deployment and scalability.

## System Architecture

The application is comprised of a FastAPI backend and a static frontend, communicating via a RESTful API. The entire system is designed to be run within Docker containers, ensuring a consistent and reproducible environment.

### Services and Technologies

- **Backend**: Python 3.11 with FastAPI
- **Database**: MongoDB for all persistent data, including user information, chat sessions, and long-term memory.
- **AI Models**:
	- **Primary**: Google's Gemini Pro for response generation.
	- **Fallback**: An NVIDIA-based model for summarisation, accessed via a dedicated API.
- **Containerisation**: Docker and Docker Compose for service orchestration.
- **Frontend**: Static HTML, CSS, and vanilla JavaScript.

### Retrieval-Augmented Generation (RAG) Implementation

The system's contextual memory is built upon a RAG architecture to provide relevant and informed responses. This is achieved through a multi-layered memory system:

- **Short-Term Memory**: An in-memory LRU (Least Recently Used) cache stores the summaries of the last three interactions. This allows for immediate context recall within an ongoing conversation.
- **Long-Term Memory**: The summaries of the last twenty interactions for each patient are persisted in MongoDB. This provides a deeper historical context for recurring patients, allowing the system to reference past conversations and maintain continuity over time.

When a query is received, the system retrieves the relevant short and long-term memory summaries to build a comprehensive context. This context is then provided to the LLM model along with the user's query to generate an accurate and context-aware response.

## Key Features

- **Patient-Centric Memory**: Utilises both short-term and long-term memory to maintain context throughout conversations.
- **Persistent Chat History**: All chat sessions are saved in MongoDB, allowing for a complete history of interactions.
- **Contextual Awareness**: The system maintains the context of both the patient and the doctor in all messages and summaries.
- **User Management**: Includes features for patient search (by name or ID) and a doctor dropdown with a streamlined user creation process.
- **Modern User Interface**: The application features a sidebar for session management, modals for doctor and patient profiles, a dark/light mode, and a mobile-friendly design.
- **AI Model Integration**: The system leverages Gemini for generating responses and includes a fallback to an NVIDIA summariser.

## Getting Started

To get the project up and running, please refer to the detailed instructions in the [setup guide](./SETUP_GUIDE.md).

## Licence & Disclaimer

This project is licensed under the Apache 2.0 Licence. See the [LICENCE](./LICENCE) file for details.

The information provided by this system is for educational purposes only and is not a substitute for professional medical advice, diagnosis, or treatment. Always seek the advice of your physician or other qualified health provider with any questions you may have regarding a medical condition.

Team D1 - COS30018, Swinburne University of Technology
