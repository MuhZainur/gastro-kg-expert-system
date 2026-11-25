export function createInitialForm() {
  return {
    age: "",
    riskFactors: [],
    medications: {},
    symptoms: {},
    disabledRules: [],
    extraKnowledge: null,
    customMedications: [],
  };
}

export const appState = {
  formSchema: null,
  rulesList: null,
  form: createInitialForm(),
  lastRequest: null,
  result: null,
  previousResult: null,
  resultSource: null,
  sampleId: null,
  sampleTitle: null,
};

export function resetForm() {
  appState.form = createInitialForm();
}

export function loadRequestIntoForm(req, extraMed = null) {
  const symptoms = {};
  for (const s of req.symptoms || []) {
    symptoms[s.id] = { answer: s.answer, certainty: Number(s.certainty) };
  }
  const medications = {};
  for (const m of req.medications || []) {
    medications[m.id] = { selected: true, regular: Boolean(m.regular) };
  }
  appState.form = {
    age: req.age ?? "",
    riskFactors: [...(req.riskFactors || [])],
    medications,
    symptoms,
    disabledRules: [...(req.disabledRules || [])],
    extraKnowledge: req.extraKnowledge || null,
    customMedications: extraMed ? [extraMed] : [],
  };
}

export function buildConsultationPayload() {
  const form = appState.form;
  const ageNum = form.age === "" || form.age === null ? -1 : Number(form.age);
  const symptoms = Object.entries(form.symptoms)
    .filter(([, val]) => val.answer === "yes" || val.answer === "no")
    .map(([id, val]) => ({
      id,
      answer: val.answer,
      certainty: Number(Number(val.certainty).toFixed(1)),
    }));
  const medications = Object.entries(form.medications)
    .filter(([, val]) => val.selected)
    .map(([id, val]) => ({ id, regular: Boolean(val.regular) }));

  return {
    age: Number.isFinite(ageNum) ? ageNum : -1,
    riskFactors: [...form.riskFactors],
    medications,
    symptoms,
    disabledRules: [...form.disabledRules],
    extraKnowledge: form.extraKnowledge && form.extraKnowledge.trim() ? form.extraKnowledge : null,
  };
}
