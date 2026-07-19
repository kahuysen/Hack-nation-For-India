# Databricks notebook source
try:
    from data_eng.vector_search.materialize_delta import materialize_embeddings
except ImportError:
    from materialize_delta import materialize_embeddings

result = materialize_embeddings(spark)
display(result)
