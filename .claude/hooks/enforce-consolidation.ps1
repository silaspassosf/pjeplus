$payload = @{
  hookSpecificOutput = @{
    hookEventName = "PostToolBatch"
    additionalContext = "Apos este lote, consolide os resultados e aja. Nao abra nova rodada de Read/Grep/Glob sem necessidade objetiva. Se ja houver contexto suficiente, edite, responda ou teste."
  }
} | ConvertTo-Json -Depth 10

Write-Output $payload