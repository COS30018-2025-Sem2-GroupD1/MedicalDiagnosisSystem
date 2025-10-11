### **Definitive API Endpoint Breakdown (with Model Details)**

This document outlines all available API endpoints, their expected inputs, and their potential outputs, including the detailed structure of all data models.

#### **Account** (`/account`)
---
-   **`GET /account`**
	-   **Description:** Retrieves a list of accounts, optionally filtered by a search query.
	-   **Inputs (Query):** `q` (optional, `string`), `limit` (optional, `integer`)
	-   **Outputs (200 OK):** `list[Account]`
		-   **Account Model:**
			```json
			{
			  "id": "string",
			  "name": "string",
			  "role": "string",
			  "specialty": "string | null",
			  "created_at": "datetime",
			  "updated_at": "datetime",
			  "last_seen": "datetime"
			}
			```

-   **`POST /account`**
	-   **Description:** Creates a new account profile.
	-   **Inputs (Body):** `AccountCreateRequest`
		```json
		{
		  "name": "string",
		  "role": "string",
		  "specialty": "string | null"
		}
		```
	-   **Outputs (201 Created):** `Account` (see model above).

-   **`GET /account/{account_id}`**
	-   **Description:** Retrieves a single account by its unique ID.
	-   **Inputs (Path):** `account_id` (required, `string`)
	-   **Outputs (200 OK):** `Account` (see model above).

#### **Patient** (`/patient`)
---
-   **`GET /patient`**
	-   **Description:** Searches for patients by name.
	-   **Inputs (Query):** `q` (required, `string`)
	-   **Outputs (200 OK):** `list[Patient]`
		-   **Patient Model:**
			```json
			{
			  "id": "string",
			  "name": "string",
			  "age": "integer",
			  "sex": "string",
			  "ethnicity": "string",
			  "created_at": "datetime",
			  "updated_at": "datetime",
			  "address": "string | null",
			  "phone": "string | null",
			  "email": "string | null",
			  "medications": "list[string] | null",
			  "past_assessment_summary": "string | null",
			  "assigned_doctor_id": "string | null"
			}
			```

-   **`POST /patient`**
	-   **Description:** Creates a new patient profile.
	-   **Inputs (Body):** `PatientCreateRequest` (matches the `Patient` model, but `id`, `created_at`, `updated_at` are not provided).
	-   **Outputs (201 Created):** `Patient` (see model above).

-   **`GET /patient/{patient_id}`**
	-   **Description:** Retrieves a single patient by their unique ID.
	-   **Inputs (Path):** `patient_id` (required, `string`)
	-   **Outputs (200 OK):** `Patient` (see model above).

-   **`PATCH /patient/{patient_id}`**
	-   **Description:** Updates a patient's profile.
	-   **Inputs (Path):** `patient_id` (required, `string`)
	-   **Inputs (Body):** `PatientUpdateRequest` (all fields from the `Patient` model are optional).
	-   **Outputs (200 OK):** `Patient` (the full, updated object).

-   **`GET /patient/{patient_id}/session`**
	-   **Description:** Lists all chat sessions for a specific patient.
	-   **Inputs (Path):** `patient_id` (required, `string`)
	-   **Outputs (200 OK):** `list[Session]` (see Session model below).

#### **Session & Chat** (`/session`)
---
-   **`POST /session`**
	-   **Description:** Creates a new, empty chat session.
	-   **Inputs (Body):** `SessionCreateRequest`
		```json
		{
		  "account_id": "string",
		  "patient_id": "string",
		  "title": "string | null"
		}
		```
	-   **Outputs (201 Created):** `Session`
		-   **Session Model:**
			```json
			{
			  "id": "string",
			  "account_id": "string",
			  "patient_id": "string",
			  "title": "string",
			  "created_at": "datetime",
			  "updated_at": "datetime",
			  "messages": "list[Message]"
			}
			```
		-   **Message Model (nested in Session):**
			```json
			{
			  "id": "integer",
			  "sent_by_user": "boolean",
			  "content": "string",
			  "timestamp": "datetime"
			}
			```

-   **`GET /session/{session_id}`**
	-   **Description:** Retrieves a session's metadata and all its messages.
	-   **Inputs (Path):** `session_id` (required, `string`)
	-   **Outputs (200 OK):** `Session` (see model above).

-   **`DELETE /session/{session_id}`**
	-   **Description:** Deletes a chat session.
	-   **Inputs (Path):** `session_id` (required, `string`)
	-   **Outputs (204 No Content):** Empty response.

-   **`GET /session/{session_id}/messages`**
	-   **Description:** Lists all messages for a session.
	-   **Inputs (Path):** `session_id` (required, `string`)
	-   **Outputs (200 OK):** `list[Message]` (see model above).

-   **`POST /session/{session_id}/messages`**
	-   **Description:** Posts a message to a session and gets a generated response.
	-   **Inputs (Path):** `session_id` (required, `string`)
	-   **Inputs (Body):** `ChatRequest`
		```json
		{
		  "account_id": "string",
		  "patient_id": "string",
		  "message": "string"
		}
		```
	-   **Outputs (200 OK):** `ChatResponse`
		```json
		{
		  "response": "string",
		  "session_id": "string",
		  "timestamp": "datetime",
		  "medical_context": "string | null"
		}
		```

#### **EMR (Electronic Medical Records)** (`/emr`)
---
> **Note:** These endpoints represent an older architectural pattern and have not been integrated into the main `MemoryManager` service.

-   **`GET /emr/patient/{patient_id}`**: Gets all EMR entries for a patient.
	-   **Outputs (200 OK):** `list[EMRResponse]`
		-   **EMRResponse Model:**
			```json
			{
			  "emr_id": "string",
			  "patient_id": "string",
			  "doctor_id": "string",
			  "message_id": "string",
			  "session_id": "string",
			  "original_message": "string",
			  "extracted_data": {
				"diagnosis": "list[string]",
				"symptoms": "list[string]",
				"medications": "list[Medication]",
				"vital_signs": "VitalSigns | null",
				"lab_results": "list[LabResult]",
				"procedures": "list[string]",
				"notes": "string | null"
			  },
			  "confidence_score": "float",
			  "created_at": "datetime",
			  "updated_at": "datetime"
			}
			```
-   **`POST /emr/extract`**: Extracts EMR data from a message.
	-   **Inputs (Query):** `patient_id`, `doctor_id`, `message_id`, `session_id`, `message` (all `string`).
	-   **Outputs (200 OK):** `{"emr_id": "string", "message": "string"}`.
-   *(Other EMR endpoints follow a similar pattern, using the models defined in `emr/models/emr.py`)*

#### **Utilities**
---
-   **`POST /summarise`**
	-   **Description:** Summarises text into a short title.
	-   **Inputs (Body):** `SummariseRequest`
		```json
		{
		  "text": "string",
		  "max_words": "integer"
		}
		```
	-   **Outputs (200 OK):** `SummariseResponse`
		```json
		{
		  "title": "string"
		}
		```

-   **`POST /audio/transcribe`**
	-   **Description:** Transcribes an audio file to text.
	-   **Inputs (Form Data):** `file` (required, `UploadFile`), `language_code` (optional, `string`).
	-   **Outputs (200 OK):** `JSON`
		```json
		{
		  "success": "boolean",
		  "transcribed_text": "string",
		  "language_code": "string",
		  "file_name": "string"
		}
		```
-   **`GET /audio/supported-formats`**: Returns `{"supported_formats": ["wav", "opus", ...], "description": "string"}`.

#### **System & Health**
---
-   **`GET /`** & **`GET /system-status`**: Serves static HTML pages.
-   **`GET /system/health`**: Returns a `JSON` object detailing the status of core components (memory, embedding, API keys).
-   **`GET /system/database`**: Returns a detailed `JSON` object describing the state of each MongoDB collection (document counts, indexes, fields).
-   **`GET /audio/health`**: Returns a `JSON` object detailing the status of the audio transcription service.
-   **`GET /emr/health`**: Returns a `JSON` object with the status and document count of the EMR collection.
