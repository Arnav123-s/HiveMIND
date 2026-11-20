// Extract absolute final-token features and base logits from the pinned CPU model.
#include "llama.h"
#include <algorithm>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>

static void evaluate(llama_context *ctx, llama_batch &batch, const std::vector<int> &ids, size_t start) {
    batch.n_tokens = 0;
    for (size_t j = start; j < ids.size(); ++j) {
        int idx = batch.n_tokens++;
        batch.token[idx] = ids[j];
        batch.pos[idx] = j;
        batch.n_seq_id[idx] = 1;
        batch.seq_id[idx][0] = 0;
        batch.logits[idx] = j + 1 == ids.size();
    }
    if (llama_decode(ctx, batch)) throw std::runtime_error("native prefill failed");
}

static void write_floats(std::ofstream &out, const float *values, size_t count) {
    if (!values) throw std::runtime_error("native result unavailable");
    out.write(reinterpret_cast<const char*>(values), count * sizeof(float));
    if (!out) throw std::runtime_error("could not write result");
}

static void extract(llama_model *model, llama_context *ctx, const char *source, const char *destination) {
    std::ifstream input(source, std::ios::binary);
    std::ofstream out(destination, std::ios::binary);
    if (!input || !out) throw std::runtime_error("cannot open data files");
    auto batch = llama_batch_init(512, 0, 1);
    std::vector<int> previous;
    std::string text;
    int count = 0;
    while (std::getline(input, text, '\0')) {
        std::vector<int> ids(512);
        const int n = llama_tokenize(model, text.data(), text.size(), ids.data(), ids.size(), false, true);
        if (n < 2 || n >= 512) throw std::runtime_error("prompt outside context contract");
        ids.resize(n);
        size_t prefix = 0;
        while (prefix < std::min(previous.size(), ids.size() - 1) && previous[prefix] == ids[prefix]) ++prefix;
        if (!llama_kv_cache_seq_rm(ctx, 0, prefix, -1)) throw std::runtime_error("cannot reset cached suffix");
        llama_set_embeddings(ctx, true);
        evaluate(ctx, batch, ids, prefix);
        write_floats(out, llama_get_embeddings_ith(ctx, -1), llama_model_n_embd(model));
        if (!llama_kv_cache_seq_rm(ctx, 0, n - 1, -1)) throw std::runtime_error("cannot reset final token");
        llama_set_embeddings(ctx, false);
        evaluate(ctx, batch, ids, n - 1);
        write_floats(out, llama_get_logits_ith(ctx, -1), llama_n_vocab(model));
        std::cout << "row " << ++count << " tokens " << n << " reused " << prefix << std::endl;
        previous = std::move(ids);
    }
    llama_batch_free(batch);
}

int main(int argc, char **argv) {
    if (argc != 4) return 1;
    llama_backend_init();
    auto mp = llama_model_default_params();
    mp.n_gpu_layers = 0;
    auto model = llama_model_load_from_file(argv[1], mp);
    if (!model) return 2;
    auto cp = llama_context_default_params();
    cp.n_threads = cp.n_threads_batch = 1;
    cp.n_ctx = 2048; cp.n_batch = cp.n_ubatch = 512;
    cp.attention_type = LLAMA_ATTENTION_TYPE_CAUSAL;
    cp.embeddings = true; cp.pooling_type = LLAMA_POOLING_TYPE_NONE;
    auto ctx = llama_init_from_model(model, cp);
    if (!ctx) return 3;
    int status = 0;
    try { extract(model, ctx, argv[2], argv[3]); }
    catch (const std::exception &e) { std::cerr << e.what() << std::endl; status = 4; }
    llama_free(ctx);
    llama_free_model(model);
    llama_backend_free();
    return status;
}
