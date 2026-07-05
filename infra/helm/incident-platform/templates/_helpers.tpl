{{- define "incident-platform.chart" -}}
{{ .Chart.Name }}-{{ .Chart.Version | replace "+" "_" }}
{{- end }}

{{- define "incident-platform.commonLabels" -}}
app.kubernetes.io/part-of: incident-platform
app.kubernetes.io/managed-by: {{ .Release.Service }}
helm.sh/chart: {{ include "incident-platform.chart" . }}
{{- end }}

{{- define "incident-platform.selectorLabels" -}}
app.kubernetes.io/name: {{ .name }}
app.kubernetes.io/part-of: incident-platform
{{- end }}

{{- define "incident-platform.image" -}}
{{- $root := .root -}}
{{- $image := .image -}}
{{- printf "%s/%s:%s" $root.Values.global.imageRegistry $image.repository $image.tag -}}
{{- end }}

{{- define "incident-platform.databaseUrl" -}}
{{- $db := . -}}
{{- printf "postgresql+psycopg://%s:%s@%s:%v/%s" $db.username $db.password $db.host 5432 $db.database -}}
{{- end }}

