{{/*
EIOS Helm Chart — template helpers
*/}}

{{- define "eios.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{- define "eios.fullname" -}}
{{- $name := default .Chart.Name .Values.nameOverride }}
{{- if contains $name .Release.Name }}
{{- .Release.Name | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}

{{- define "eios.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{- define "eios.labels" -}}
helm.sh/chart: {{ include "eios.chart" . }}
{{ include "eios.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{- define "eios.selectorLabels" -}}
app.kubernetes.io/name: {{ include "eios.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{- define "eios.serviceAccountName" -}}
{{- if .Values.serviceAccount.create }}
{{- default (include "eios.fullname" .) .Values.serviceAccount.name }}
{{- else }}
{{- default "default" .Values.serviceAccount.name }}
{{- end }}
{{- end }}

{{/*
Image name with optional global registry prefix.
Usage: {{ include "eios.image" (dict "repo" .Values.image.backend.repository "tag" .Values.image.backend.tag "global" .Values.global) }}
*/}}
{{- define "eios.image" -}}
{{- $registry := .global.imageRegistry | default "" }}
{{- if $registry }}
{{- printf "%s/%s:%s" $registry .repo .tag }}
{{- else }}
{{- printf "%s:%s" .repo .tag }}
{{- end }}
{{- end }}

{{/*
Secret name — use existingSecret when set, otherwise the chart-managed secret.
*/}}
{{- define "eios.secretName" -}}
{{- if .Values.existingSecret }}
{{- .Values.existingSecret }}
{{- else }}
{{- include "eios.fullname" . }}-credentials
{{- end }}
{{- end }}

{{/*
Database URL — derived from postgresql subchart when enabled, otherwise from secrets.
*/}}
{{- define "eios.databaseUrl" -}}
{{- if .Values.postgresql.enabled }}
{{- $host := printf "%s-postgresql" (include "eios.fullname" .) }}
{{- printf "postgresql+asyncpg://%s:%s@%s:5432/%s" .Values.postgresql.auth.username .Values.postgresql.auth.password $host .Values.postgresql.auth.database }}
{{- else }}
{{- .Values.secrets.databaseUrl }}
{{- end }}
{{- end }}

{{/*
Redis URL — derived from in-cluster Redis when enabled.
*/}}
{{- define "eios.redisUrl" -}}
{{- if .Values.redis.enabled }}
{{- printf "redis://%s-redis-master:6379/0" (include "eios.fullname" .) }}
{{- else }}
{{- .Values.secrets.redisUrl }}
{{- end }}
{{- end }}

{{/*
Redis blacklist URL.
*/}}
{{- define "eios.redisBlacklistUrl" -}}
{{- if .Values.redisBlacklist.enabled }}
{{- printf "redis://%s-redis-blacklist:6379/0" (include "eios.fullname" .) }}
{{- else }}
{{- .Values.secrets.redisBlacklistUrl }}
{{- end }}
{{- end }}
