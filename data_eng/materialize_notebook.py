# Databricks notebook source
try:
    from data_eng.materialize import materialize_all
except ImportError:
    from materialize import materialize_all

outputs = materialize_all(spark)
display(outputs)
