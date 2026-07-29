# Story to geometry

## Choose the semantic job first

Assign each narration beat one primary job. If a sentence needs two unrelated geometries, split it into two scenes. Convert abstract claims into explicit spatial relationships before adding decoration.

| Narration job | Diagram family | Build order |
|---|---|---|
| Identify a term | Wordmark, underline, chip, or single card | term → supporting mark |
| Identify a person or product | Portrait/logo plus name in one identity card | image → name → descriptor |
| Add numeric proof | Metric card beside or below the claim | claim → metric → interpretation |
| Show ordered steps | Horizontal or vertical node scaffold with connectors | inactive scaffold → activate in reading order |
| Show downstream failure | Reuse the process geometry and mutate state | fault → connector → downstream error states |
| Show modularity | Repeated equal-weight tiles in a grid | loose tiles → aligned grid → labels |
| Divide responsibility | Two columns or panels with one explicit relation | headline → first side → second side → result |
| Show containment | Parent boundary around child elements | children → boundary → allowed or blocked path |
| Show dependencies | Root and child cards connected behind the cards | nodes → connectors → active route |
| Demonstrate an implementation | User-supplied UI panel inside the explainer canvas | concept → UI → result |
| Map problem to solution | Repeated left-item, arrow, right-item rows | append rows in narration order |
| State a verdict | Completed diagram dimmed under a callout | complete state → dim → verdict |
| Reset abstraction | One centered illustration or abstract object | replace the entire scene stage |

## Preserve geometry while the conceptual model stays the same

When narration says the same system becomes active, fails, passes, or is constrained, keep positions and relationships stable and mutate visual state. Replace the layout only when the conceptual model changes, such as moving from a pipeline to modular tiles.

Do not move objects merely to create activity. Readability comes from seeing a stable scaffold acquire meaning.

## Use one dominant relation per scene

- Sequence: one baseline and one reading direction.
- Comparison: two clear sides and one relation or verdict.
- Hierarchy: one parent/child direction.
- Containment: one visible boundary and a deliberate entry point.
- Network: connectors behind nodes; reduce labels until crossings remain readable.
- Enumeration: repeated cards or rows with stable alignment.

## Storyboard schema

Record these fields for every scene:

```text
scene_id
narration_start / narration_end
semantic_job
diagram_family
cue_keys[]
neutral_start
triggered_changes[]
final_hold
exit
required_assets[]
production_notes
```

Reject a scene that has multiple unrelated semantic jobs or animation changes without named cues.
