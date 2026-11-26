export default function SegmentScores({ segments }) {
  if (!segments?.length) return <span>—</span>
  return (
    <ul className="segment-scores" aria-label="Normalized world scores">
      {segments.map((segment) => (
        <li key={segment.range}>
          <span>{segment.world != null ? `World ${segment.world}` : `Stages ${segment.range}`}</span>
          <strong>{segment.score == null ? (segment.status === 'unplayed' ? 'Unplayed' : 'Incomplete') : `${segment.score}/100`}</strong>
        </li>
      ))}
    </ul>
  )
}
