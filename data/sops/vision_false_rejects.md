# SOP-204: Vision Inspection False Rejects (SYNTHETIC EXAMPLE)
Applies to: inline vision inspection stations.
Symptoms: vision_false_reject count rising, good parts failing inspection, repeated vision_fault stops, often on one shift.
Likely causes: lighting intensity degradation or dirty lens, ambient light changes, camera focus drift, outdated golden sample.
Steps:
1. Run the golden sample and a known bad sample. Record the scores.
2. Inspect and clean the lens and light cover. Check light controller intensity against the baseline setting.
3. Compare current images to the saved reference images for brightness and contrast.
4. Recalibrate the camera and lighting. Replace the light source if intensity cannot be restored.
5. Re-validate with the golden sample set before release.
Escalate to the vision engineer if false rejects persist after recalibration.
