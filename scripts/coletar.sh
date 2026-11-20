#!/bin/zsh
# Coleta das lojas, usada pelo agendamento do launchd (ver README). Também pode ser rodada à mão.
# Carrega credenciais/env, roda o coletor (últimos 7 dias) e anexa a saída ao log.
# Em caso de falha, mostra uma notificação no macOS.

cd "${0:A:h}/.." || exit 1
LOG="$HOME/Library/Logs/analise-apps.log"

{
  echo "=== $(date '+%Y-%m-%d %H:%M:%S')"
  set -a; source credenciais/env; set +a
  .venv/bin/python -m coletor.main
  rc=$?
  echo "saída: $rc"
} >> "$LOG" 2>&1

if [[ $rc -ne 0 ]]; then
  osascript -e "display notification \"A coleta falhou (código $rc). Veja ~/Library/Logs/analise-apps.log\" with title \"Painel das lojas\""
fi
exit $rc
