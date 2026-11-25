/**
 * Cloudflare Worker do Mundo em Questão:
 * 1) Serve normalmente todos os arquivos estáticos da pasta ./publico.
 * 2) A cada 1 hora exata (Cron Trigger "0 * * * *"), dispara o workflow_dispatch
 *    no GitHub Actions para atualizar noticias.json sem atrasos nem descartes.
 */
export default {
  async fetch(request, env) {
    return env.ASSETS.fetch(request);
  },

  async scheduled(_event, env, ctx) {
    const token = env.GITHUB_TOKEN;
    if (!token) {
      console.error("Secret GITHUB_TOKEN nao configurada no Cloudflare Worker.");
      return;
    }

    const url =
      "https://api.github.com/repos/utilidadepublica48-spec/mundoemquestao/actions/workflows/buscar-noticias.yml/dispatches";

    ctx.waitUntil(
      fetch(url, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
          Accept: "application/vnd.github+json",
          "Content-Type": "application/json",
          "User-Agent": "mundoemquestao-cloudflare-cron",
        },
        body: JSON.stringify({ ref: "main" }),
      }).then(async (res) => {
        if (!res.ok) {
          console.error("Falha ao disparar GitHub Actions:", res.status, await res.text());
        } else {
          console.log("Atualizacao horaria disparada com sucesso no GitHub Actions.");
        }
      })
    );
  },
};
