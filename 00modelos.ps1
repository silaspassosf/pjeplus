# FORÇA OPENAI-COMPATIBLE (ignora Anthropic)
$env:CLAUDE_CODE_USE_OPENAI = "1"
$env:CLAUDE_CODE_USE_ANTHROPIC = "0"
$env:CLAUDE_CODE_PRIMARY_PROVIDER = "openai"
# ---- BASE (GROQ+Qwen 2.5) ----
$env:OPENAI_API_KEY="sua-chave-aqui"
$env:OPENAI_BASE_URL="https://api.groq.com/openai/v1"
$env:OPENAI_MODEL="qwen/qwen3-32b"
# ---- FUNÇÕES DE TROCA ----

function use-groq {
    $env:OPENAI_API_KEY="sua-chave-aqui"
    $env:OPENAI_BASE_URL="https://api.groq.com/openai/v1"
    $env:OPENAI_MODEL="qwen/qwen3-32b"
    Write-Host "🆓 GROQ Qwen2.5" -ForegroundColor Green
}

function local-phi {
    $env:OPENAI_BASE_URL="http://localhost:11434/v1"
    $env:OPENAI_API_KEY="sua-chave-aqui"
    $env:OPENAI_MODEL="phi4-mini"
    Write-Host "🧠 Phi4-Mini local (120-200 t/s)" -ForegroundColor Cyan
}

function qwen30 {
  $env:OPENAI_BASE_URL="http://localhost:11434/v1"
  $env:OPENAI_API_KEY="sua-chave-aqui"
  $env:OPENAI_MODEL="qwen3-coder:30b"
  Write-Host "⚡ Qwen3 Coder 30B local (40-60 t/s)" -ForegroundColor Green
}
function use-plus {
    $env:OPENAI_API_KEY="sua-chave-aqui"
    $env:OPENAI_BASE_URL="https://dashscope-intl.aliyuncs.com/compatible-mode/v1"
    $env:OPENAI_MODEL="qwen3-coder-plus"
    Write-Host "🚀 Qwen Coder Plus (Alibaba)" -ForegroundColor Yellow
}

function use-gemini {
    $env:OPENAI_API_KEY="sua-chave-aqui"
    $env:OPENAI_BASE_URL="https://generativelanguage.googleapis.com/v1beta/openai"
    $env:OPENAI_MODEL="gemini-2.0-flash"
    Write-Host "💎 Gemini Flash (Google)" -ForegroundColor Blue
}

function use-deepseek {
    $env:OPENAI_API_KEY="sua-chave-aqui"
    $env:OPENAI_BASE_URL="https://api.deepseek.com/v1"
    $env:OPENAI_MODEL="deepseek-chat"
    Write-Host "🔵 DeepSeek Chat" -ForegroundColor Cyan
}

function use-kimi {
    $env:OPENAI_API_KEY="sua-chave-aqui"
    $env:OPENAI_BASE_URL="https://api.moonshot.ai/v1"
    $env:OPENAI_MODEL="moonshot-v1-auto"
    Write-Host "🌙 Kimi (Moonshot)" -ForegroundColor Magenta
}

function use-openai {
    $env:OPENAI_API_KEY="sua-chave-aqui"
    $env:OPENAI_BASE_URL="https://api.openai.com/v1"
    $env:OPENAI_MODEL="gpt-4.1"
    Write-Host "🤖 GPT-4.1 (OpenAI)" -ForegroundColor White
}

function use-openrouter {
    $env:OPENAI_API_KEY="sua-chave-aqui"
    $env:OPENAI_BASE_URL="https://openrouter.ai/api/v1"
    $env:OPENAI_MODEL="openrouter/free"
    Write-Host "🆓 OpenRouter Free (modelo automático)" -ForegroundColor Green
}

function use-cerebras {
    $env:OPENAI_API_KEY="sua-chave-aqui"
    $env:OPENAI_BASE_URL="https://api.cerebras.ai/v1"
    $env:OPENAI_MODEL="llama3.1-8b"
    Write-Host "🧠 Cerebras"
}

function use-zai {
    $env:OPENAI_API_KEY="sua-chave-aqui"
    $env:OPENAI_BASE_URL="https://api.z.ai/api/paas/v4"
    $env:OPENAI_MODEL="glm-4.7-flash"
    Write-Host "💻 Z.AI - GLM-4.7-Flash (FREE, coding)" -ForegroundColor Magenta
}

function modelo {
    Write-Host "Modelo atual: $env:OPENAI_MODEL @ $env:OPENAI_BASE_URL" -ForegroundColor Cyan
}

function Test-Api {
  Write-Host "🔍 Testando $env:OPENAI_BASE_URL/models..." -ForegroundColor Cyan
  $headers = @{Authorization="Bearer $env:OPENAI_API_KEY"}
  try {
    $res = iwr "$env:OPENAI_BASE_URL/models" -Headers $headers -TimeoutSec 10
    $models = ($res.Content | ConvertFrom-Json).data.id
    Write-Host "✅ Modelos disponíveis:" -ForegroundColor Green
    $models | Select-Object -First 5 | Format-Table
  } catch {
    Write-Host "❌ ERRO: $($_.Exception.Message)" -ForegroundColor Red
  }
}