# Box and Connector Motion Pattern

Use this reference when the source relies on outlined cards, orthogonal connectors, node graphs, compact process diagrams, or a persistent canvas that changes state over time.

## Visual anatomy

- Use one quiet canvas with a strong outer frame.
- Assign one semantic accent color to active or target nodes.
- Use hard offset shadows and consistent border widths.
- Keep connector paths behind all cards.
- Anchor small metadata to the frame edges so the composition reads as a designed system, not loose boxes.

## Reading-order choreography

1. Reveal the frame and section label.
2. Land the focus card.
3. Land the next endpoint.
4. Draw the connector after both endpoints are readable.
5. Add supporting cards one at a time.
6. Hold long enough to read the complete graph.
7. Compress and fade the old cluster while the next state overlaps into the same canvas.
8. Use one consistent scene transition when the topic changes.

Typical values at 30 fps:

- card entrance: 0.45–0.60 s, `scale: 0.82 → 1`, `y: 18 → 0`, `power3.out`
- path draw: 0.35–0.60 s, `power2.out`
- state swap overlap: 0.10–0.20 s
- medium horizontal push: 0.35–0.50 s, `power3.inOut`
- final dwell: at least 0.8–1.0 s

## Connector initialization

Every connector must be hidden at composition time zero. Hiding it only at its later cue is too late: the browser will render the default visible SVG stroke before that cue.

```js
const tl = gsap.timeline({ paused: true });
const connectorLengths = new Map();

document.querySelectorAll(".connector").forEach((path) => {
  const length = path.getTotalLength();
  connectorLengths.set(path, length);
  tl.set(path, {
    strokeDasharray: length,
    strokeDashoffset: length,
  }, 0);
});

function drawPath(selector, at, duration = 0.5) {
  tl.to(selector, {
    strokeDashoffset: 0,
    duration,
    ease: "power2.out",
  }, at);
}
```

Give junction rectangles or dots their own IDs and initialize their opacity to zero. Reveal them with the connector that owns them.

## Card entrance

Use explicit `fromTo` states so seeking to any frame produces the same pixels:

```js
function pop(selector, at, duration = 0.52) {
  tl.fromTo(
    selector,
    { scale: 0.82, opacity: 0, y: 18 },
    { scale: 1, opacity: 1, y: 0, duration, ease: "power3.out" },
    at,
  );
}
```

Avoid exaggerated bounce. A smooth settle is closer to editorial technical motion than a cartoon spring.

## Persistent-canvas state swap

Use a short overlap rather than an empty reset:

```js
tl.to("#old-graph", {
  scale: 0.94,
  opacity: 0,
  duration: 0.42,
  ease: "power2.in",
}, 12.9);

tl.fromTo("#new-graph",
  { scale: 0.97, opacity: 0 },
  { scale: 1, opacity: 1, duration: 0.56, ease: "power3.out" },
  13.05,
);
```

Start the new focus card during the cluster overlap. Do not leave a half-second blank canvas between graph states.

## Failure scan

- stray line or square before the first card
- connector drawn through text because z-order is wrong
- every card entering at once
- new graph appearing fully formed
- blank frame between graph states
- different transition style at every change
- source copy or source imagery left in the replica
