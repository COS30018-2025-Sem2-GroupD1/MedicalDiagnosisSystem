# Medical Knowledge Base for the Medical AI Assistant

MEDICAL_KB = {
	"symptoms": {
		"fever": "Fever is a temporary increase in body temperature, often due to illness. Normal body temperature is around 98.6°F (37°C).",
		"headache": "Headache is pain in the head or upper neck. Common types include tension headaches, migraines, and cluster headaches.",
		"cough": "Cough is a sudden expulsion of air from the lungs. It can be dry or productive (bringing up mucus).",
		"fatigue": "Fatigue is extreme tiredness that doesn't improve with rest. It can be caused by various medical conditions.",
		"nausea": "Nausea is a feeling of sickness with an inclination to vomit. It can be caused by various conditions including infections, medications, and pregnancy.",
		"dizziness": "Dizziness is a sensation of lightheadedness or unsteadiness. It can be caused by inner ear problems, low blood pressure, or neurological conditions.",
		"chest pain": "Chest pain can have many causes, from muscle strain to serious heart conditions. Any unexplained chest pain should be evaluated by a healthcare provider.",
		"shortness of breath": "Shortness of breath, or dyspnea, is difficulty breathing. It can be caused by respiratory, cardiac, or other medical conditions."
	},
	"conditions": {
		"hypertension": "Hypertension (high blood pressure) is a common condition that affects the arteries. It's often called the 'silent killer' because it usually has no symptoms.",
		"diabetes": "Diabetes is a chronic disease that affects how your body turns food into energy. There are two main types: Type 1 and Type 2.",
		"asthma": "Asthma is a condition that affects the airways in the lungs. It can cause wheezing, shortness of breath, chest tightness, and coughing.",
		"pneumonia": "Pneumonia is an infection that inflames the air sacs in one or both lungs. It can be caused by bacteria, viruses, or fungi.",
		"heart disease": "Heart disease refers to various conditions affecting the heart, including coronary artery disease, heart failure, and arrhythmias.",
		"arthritis": "Arthritis is inflammation of the joints, causing pain and stiffness. The most common types are osteoarthritis and rheumatoid arthritis.",
		"depression": "Depression is a mental health disorder characterized by persistently depressed mood or loss of interest in activities.",
		"anxiety": "Anxiety disorders involve excessive fear or worry that can interfere with daily activities and relationships."
	},
	"medications": {
		"aspirin": "Aspirin is a common medication used to treat pain, fever, and inflammation. It's also used to prevent heart attacks and strokes.",
		"ibuprofen": "Ibuprofen is a nonsteroidal anti-inflammatory drug (NSAID) used to reduce fever and treat pain or inflammation.",
		"acetaminophen": "Acetaminophen is used to treat pain and reduce fever. It's generally safe when used as directed.",
		"antibiotics": "Antibiotics are medications that fight bacterial infections. They don't work against viral infections like colds or flu.",
		"insulin": "Insulin is a hormone that helps control blood sugar levels. It's essential for people with Type 1 diabetes and some with Type 2.",
		"statins": "Statins are medications that help lower cholesterol levels in the blood, reducing the risk of heart disease and stroke."
	},
	"procedures": {
		"blood test": "Blood tests can check for various conditions, monitor organ function, and assess overall health. Common types include CBC, metabolic panels, and lipid profiles.",
		"x-ray": "X-rays use radiation to create images of bones and some soft tissues. They're commonly used to diagnose fractures, pneumonia, and other conditions.",
		"mri": "MRI (Magnetic Resonance Imaging) uses magnetic fields and radio waves to create detailed images of organs and tissues.",
		"ct scan": "CT scans use X-rays and computer technology to create cross-sectional images of the body, useful for diagnosing various conditions."
	}
}

def search_medical_kb(query: str) -> str:
	"""Search the medical knowledge base for relevant information"""
	query_lower = query.lower()
	relevant_info = []

	for category, items in MEDICAL_KB.items():
		for key, value in items.items():
			if query_lower in key.lower() or query_lower in value.lower():
				relevant_info.append(f"{key.title()}: {value}")

	if relevant_info:
		return "\n\n".join(relevant_info[:3])  # Limit to 3 most relevant
	return ""
