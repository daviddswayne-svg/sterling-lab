import { initViewer, displayVoxels, displayComparison, setLayerVisibility } from './viewer.js';

// Use relative path for production proxy
const API_BASE = window.location.origin + "/audit/api";

const dzBaseline = document.getElementById('drop-zone-baseline');
const dzDamage = document.getElementById('drop-zone-damage');
const fileBaseline = document.getElementById('file-baseline');
const fileDamage = document.getElementById('file-damage');

const auditControls = document.getElementById('audit-controls');
const btnCompare = document.getElementById('btn-compare');
const toggleBaseline = document.getElementById('toggle-baseline');
const toggleDamage = document.getElementById('toggle-damage');

const progressContainer = document.getElementById('progress-container');
const progressFill = document.getElementById('progress-fill');
const progressText = document.getElementById('progress-text');

let jobs = {
    baseline: null,
    damage: null
};

initViewer();

// Setup mini dropzones
setupDropzone(dzBaseline, fileBaseline, 'baseline');
setupDropzone(dzDamage, fileDamage, 'damage');

function setupDropzone(dz, input, type) {
    dz.onclick = () => input.click();
    input.onchange = (e) => handleUpload(e.target.files[0], type, dz);
}

async function handleUpload(file, type, dz) {
    if (!file) return;

    const formData = new FormData();
    formData.append('file', file);

    dz.querySelector('.hint').innerText = "Uploading...";
    dz.classList.add('active');

    try {
        updateProgress(10, `Processing ${type} asset...`);
        progressContainer.classList.remove('hidden');

        const response = await fetch(`${API_BASE}/upload`, {
            method: 'POST',
            body: formData
        });

        const { job_id } = await response.json();
        pollJob(job_id, type, dz);
    } catch (err) {
        console.error(err);
        dz.querySelector('.hint').innerText = "Upload failed";
        dz.classList.remove('active');
    }
}

async function pollJob(jobId, type, dz) {
    const interval = setInterval(async () => {
        try {
            const response = await fetch(`${API_BASE}/status/${jobId}`);
            const job = await response.json();

            if (job.status === 'completed') {
                clearInterval(interval);
                jobs[type] = jobId;
                dz.querySelector('.hint').innerText = "✅ Ready";

                // If this is the only one, show it immediately
                if (!jobs.baseline || !jobs.damage) {
                    displayVoxels(job.result);
                }

                checkComparisonReady();
                progressContainer.classList.add('hidden');
            } else if (job.status === 'failed') {
                clearInterval(interval);
                dz.querySelector('.hint').innerText = "❌ Error";
            }
        } catch (err) {
            clearInterval(interval);
            console.error(err);
        }
    }, 1000);
}

function checkComparisonReady() {
    if (jobs.baseline && jobs.damage) {
        auditControls.style.display = 'block';
        btnCompare.disabled = false;
        btnCompare.innerText = "Run Differential Audit";
    }
}

btnCompare.onclick = async () => {
    btnCompare.disabled = true;
    btnCompare.innerText = "Analyzing Deltas...";

    try {
        const response = await fetch(`${API_BASE}/compare/${jobs.baseline}/${jobs.damage}`);
        if (!response.ok) {
            const errBody = await response.json();
            throw new Error(errBody.detail || response.statusText);
        }
        const { comparison_id, metrics } = await response.json();

        const voxResponse = await fetch(`${API_BASE}/voxels/${comparison_id}`);
        if (!voxResponse.ok) throw new Error("Voxel retrieval failed");

        const result = await voxResponse.json();

        displayComparison(result);

        // Update stats
        document.getElementById('audit-id').innerText = comparison_id.split('_')[1].substring(0, 8);
        const totalVoxels = result.voxels.length;
        document.getElementById('voxel-count').innerText = totalVoxels;

        // Smart Verdict Logic
        const lostPct = (metrics.lost / metrics.matching) * 100 || 0;
        const addedPct = (metrics.added / metrics.matching) * 100 || 0;

        let risk = "LOW";
        let verdict = "Audit Passed: No Significant Variance";
        let riskClass = "verdict-low";

        if (lostPct > 5 || addedPct > 5) {
            risk = "HIGH";
            verdict = `Forensic Alert: ${lostPct.toFixed(1)}% Volume Loss Detected`;
            riskClass = "verdict-high";
        } else if (lostPct > 1 || addedPct > 1) {
            risk = "MED";
            verdict = "Minor Discrepancy Detected";
            riskClass = "verdict-med";
        }

        const riskEl = document.getElementById('risk-level');
        riskEl.innerText = risk;
        riskEl.className = `risk-${risk.toLowerCase()}`;

        // Inject a verdict box if it doesn't exist
        let verdictEl = document.getElementById('audit-verdict');
        if (!verdictEl) {
            verdictEl = document.createElement('div');
            verdictEl.id = 'audit-verdict';
            btnCompare.after(verdictEl);
        }
        verdictEl.className = `verdict-box ${riskClass}`;
        verdictEl.innerText = verdict;

        btnCompare.innerText = "Audit Complete";

    } catch (err) {
        console.error(err);
        alert("Comparison Error: " + err.message);
        btnCompare.innerText = "Review Failed";
    }
};

toggleBaseline.onchange = (e) => setLayerVisibility('baseline', e.target.checked);
toggleDamage.onchange = (e) => setLayerVisibility('damage', e.target.checked);

function updateProgress(percent, text) {
    progressFill.style.width = `${percent}%`;
    progressText.innerText = text;
}
