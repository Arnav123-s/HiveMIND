// Extract final hidden states from a causal GGUF model. Adjacent prompts reuse only
// identical leading tokens. Rows come from templates/token IDs rendered by the native server.
#include "llama.h"

#include <algorithm>
#include <cstdio>
#include <fstream>
#include <sstream>
#include <stdexcept>
#include <string>
#include <utility>
#include <vector>

static void extract(llama_model *model, llama_context *ctx, const char *input, const char *output) {
    const int dim = llama_model_n_embd(model);
    llama_batch batch = llama_batch_init(512, 0, 1);
    std::vector<int> previous;
    std::ifstream rows(input);
    if (!rows) throw std::runtime_error("cannot read token rows");
    std::ofstream vectors(output, std::ios::binary);
    if (!vectors) throw std::runtime_error("cannot write hidden states");
    std::string line;
    while (std::getline(rows, line)) {
        std::istringstream row(line);
        std::vector<int> tokens;
        for (int token; row >> token;) tokens.push_back(token);
        if (tokens.empty() || tokens.size() >= 2048) throw std::runtime_error("unsupported prompt length");
        const size_t reusable = std::min(previous.size(), tokens.size() - 1);
        size_t pos = 0;
        while (pos < reusable && previous[pos] == tokens[pos]) ++pos;
        if (!llama_kv_cache_seq_rm(ctx, 0, pos, -1)) throw std::runtime_error("could not reset prompt suffix");
        while (pos < tokens.size()) {
            batch.n_tokens = 0;
            while (batch.n_tokens < 512 && pos < tokens.size()) {
                const int i = batch.n_tokens++;
                batch.token[i] = tokens[pos];
                batch.pos[i] = pos;
                batch.n_seq_id[i] = 1;
                batch.seq_id[i][0] = 0;
                batch.logits[i] = ++pos == tokens.size();
            }
            if (llama_decode(ctx, batch)) throw std::runtime_error("native prefix execution failed");
        }
        auto hidden = llama_get_embeddings_ith(ctx, -1);
        if (!hidden) throw std::runtime_error("no last hidden state");
        vectors.write(reinterpret_cast<const char*>(hidden), dim * sizeof(float));
        if (!vectors) throw std::runtime_error("could not write full hidden state");
        previous = std::move(tokens);
    }
    llama_batch_free(batch);
}

int main(int argc, char **argv) {
    if (argc != 5) return 1;
    llama_backend_init();
    auto mp = llama_model_default_params();
    mp.n_gpu_layers = 0;
    auto model = llama_model_load_from_file(argv[1], mp);
    if (!model) return 2;
    auto cp = llama_context_default_params();
    cp.n_threads = cp.n_threads_batch = std::stoi(argv[4]);
    cp.n_ctx = 2048; cp.n_batch = cp.n_ubatch = 512;
    cp.embeddings = true;
    cp.pooling_type = LLAMA_POOLING_TYPE_NONE;
    cp.attention_type = LLAMA_ATTENTION_TYPE_CAUSAL;
    auto ctx = llama_init_from_model(model, cp);
    if (!ctx) return 3;
    int status = 0;
    try {
        extract(model, ctx, argv[2], argv[3]);
    } catch (const std::exception &e) {
        std::fprintf(stderr, "%s\n", e.what());
        status = 4;
    }
    llama_free(ctx);
    llama_free_model(model);
    llama_backend_free();
    return status;
}
