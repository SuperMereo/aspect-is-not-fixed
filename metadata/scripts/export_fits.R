#!/usr/bin/env Rscript
# Export the derived measures and model-fit values that the Layers release
# carries, from the fits and caches written by analysis/reproduce.ipynb.
#
# This is the only part of the metadata pipeline that needs R: the fits are
# brmsfit objects. Everything is read off the same fits the paper reports,
# with no refitting. Run from the repository root or from metadata/:
#
#   Rscript metadata/scripts/export_fits.R
#
# Inputs (written by analysis/reproduce.ipynb; untracked, ~1.1 GB):
#   analysis/fits/cloze-latent.rds       Experiment 1a fit (§2)
#   analysis/fits/proportion-latent.rds  Experiment 1b fit (§3)
#   analysis/fits/similarity.rds         Experiment 2 fit (§5)
#   analysis/cache/sentence_measures.rds per-sentence posterior-mean logits (§4)
#   analysis/cache/pair_measures.rds     per-pair aspectual match (§4)
#
# Outputs (tracked, small, deterministic): metadata/cache/
#   sentence_measures.csv  312 sentences: the three §4 logits + the time unit
#                          each sentence was evaluated at
#   pair_measures.csv      750 Experiment 2 pairs: aspectual match (overall and
#                          per logit) and the same-sense probability (§5)
#   fit_parameters.csv     population-level effects, random-effect SDs, and
#                          distributional parameters of the three fits
#   sense_proportions.csv  posterior p(sense | verb) for each (roleset,
#                          concreteness) sense, per Experiment 1 fit
#   sense_weights.csv      each sentence's posterior weights over its verb's
#                          senses (the multi-membership weights), per fit
suppressPackageStartupMessages({
  library(readr); library(dplyr); library(tidyr); library(brms); library(posterior)
})
if (basename(getwd()) == "scripts") setwd("../..")
if (basename(getwd()) == "metadata") setwd("..")
stopifnot(file.exists("data/data-cloze.csv"))
source("analysis/src/latent_senses.R")
out <- "metadata/cache"
dir.create(out, showWarnings = FALSE, recursive = TRUE)
r6 <- function(x) signif(x, 6)
write <- function(d, f) { write_csv(d, file.path(out, f), na = ""); cat(sprintf("  %s: %d rows\n", f, nrow(d))) }

# ---- §4 per-sentence time unit (same computation as the notebook) ----------
log_minutes_table <- c(
  milliseconds = -log(60) - log(1000), seconds = -log(60), minutes = 0,
  hours = log(60), days = log(60) + log(24), weeks = log(60) + log(24) + log(7),
  months = log(60) + log(24) + log(4.35 * 7),
  years = log(60) + log(24) + log(4.35 * 7 * 12),
  decades = log(60) + log(24) + log(4.35 * 7 * 12 * 10),
  centuries = log(60) + log(24) + log(4.35 * 7 * 12 * 100),
  millenia = log(60) + log(24) + log(4.35 * 7 * 12 * 1000))
kde_mode <- function(x) {
  if (length(x) < 2) return(x[1])
  d <- density(x, bw = "nrd0", n = 2048); d$x[which.max(d$y)]
}
cloze <- read_csv("data/data-cloze.csv", show_col_types = FALSE) %>%
  filter(clause_type == "episodic") %>%
  mutate(lm = log_minutes_table[as.character(duration)] + log(numeral))
per_sent_eval <- cloze %>% group_by(verb, sentence) %>%
  summarize(mode_logmin = kde_mode(lm), .groups = "drop") %>% rowwise() %>%
  mutate(eval_time_unit = names(log_minutes_table)[which.min(abs(log_minutes_table - mode_logmin))]) %>%
  ungroup()

sm <- readRDS("analysis/cache/sentence_measures.rds")
sm <- sm %>% left_join(per_sent_eval %>% dplyr::select(sentence, eval_time_unit), by = "sentence") %>%
  mutate(across(c(cloze, overlap_in, overlap_for), r6)) %>% arrange(sentence)
stopifnot(nrow(sm) == 312, !anyNA(sm$eval_time_unit))
write(sm, "sentence_measures.csv")

# ---- fits --------------------------------------------------------------------
tab <- sense_tables()
fits <- list(cloze = "analysis/fits/cloze-latent.rds",
             proportion = "analysis/fits/proportion-latent.rds",
             similarity = "analysis/fits/similarity.rds")
params <- list(); props <- list(); weights <- list()
for (nm in names(fits)) {
  cat(sprintf("reading %s ...\n", fits[[nm]]))
  m <- readRDS(fits[[nm]])
  d <- as_draws_matrix(m)
  keep <- grep("^(b_|sd_|cor_|phi$|cutzero$|cutone$|eps$)", colnames(d), value = TRUE)
  s <- summarise_draws(subset_draws(d, variable = keep), mean, median,
                       ~quantile2(.x, probs = c(0.025, 0.975)), rhat, ess_bulk, ess_tail)
  params[[nm]] <- s %>% mutate(fit = nm, .before = 1) %>%
    mutate(kind = case_when(grepl("^b_", variable) ~ "population-level",
                            grepl("^sd_", variable) ~ "group-level-sd",
                            grepl("^cor_", variable) ~ "group-level-correlation",
                            TRUE ~ "distributional"), .after = variable)
  if (nm %in% c("cloze", "proportion")) {
    ta <- align_senses(tab, standata(m), m$data)
    ps <- summarise_draws(subset_draws(d, variable = sprintf("pi_sense[%d]", ta$senses$sense)),
                          mean, ~quantile2(.x, probs = c(0.025, 0.975)))
    props[[nm]] <- tibble(fit = nm, verb = ta$senses$verb, roleset = ta$senses$sense_id,
                          concreteness = ta$senses$concreteness,
                          mean = ps$mean, q2.5 = ps$q2.5, q97.5 = ps$q97.5)
    wt <- tab$slots %>% dplyr::select(item, slot, sentence, verb, verb_sense)
    ws <- summarise_draws(subset_draws(d, variable = sprintf("Wt[%d,%d]", wt$item, wt$slot)),
                          mean, ~quantile2(.x, probs = c(0.025, 0.975)))
    weights[[nm]] <- wt %>% mutate(fit = nm, .before = 1) %>%
      mutate(roleset = sub(":.*", "", sub("_(concrete|abstract)$", "", verb_sense)),
             concreteness = sub(".*_", "", verb_sense),
             mean = ws$mean, q2.5 = ws$q2.5, q97.5 = ws$q97.5) %>%
      dplyr::select(fit, sentence, verb, roleset, concreteness, mean, q2.5, q97.5)
  }
  if (nm == "proportion") {
    pm <- readRDS("analysis/cache/pair_measures.rds")
    pm$p_same_sense <- same_sense_prob(m, tab, pm$sentence1, pm$sentence2)
  }
  rm(m, d); gc()
}
P <- bind_rows(params) %>% mutate(across(where(is.double), r6)) %>% arrange(fit, kind, variable)
write(P, "fit_parameters.csv")
write(bind_rows(props) %>% mutate(across(where(is.double), r6)) %>% arrange(fit, verb, roleset, concreteness),
      "sense_proportions.csv")
write(bind_rows(weights) %>% mutate(across(where(is.double), r6)) %>% arrange(fit, sentence, roleset, concreteness),
      "sense_weights.csv")
pm <- pm %>% dplyr::select(sentence1, sentence2, verb, aspect_match, match_cloze, match_overlap_in,
                           match_overlap_for, p_same_sense) %>%
  mutate(across(where(is.double), r6)) %>% arrange(sentence1, sentence2)
stopifnot(nrow(pm) == 750, !anyNA(pm$p_same_sense))
write(pm, "pair_measures.csv")
