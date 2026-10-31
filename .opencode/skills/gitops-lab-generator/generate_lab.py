import os


def criar_estrutura_lab(nome_lab="gitops-lab-argo-istio"):
    # Definindo a estrutura de diretórios padrão
    pastas = [
        f"{nome_lab}/manifests/app",
        f"{nome_lab}/manifests/rollouts/canary",
        f"{nome_lab}/manifests/rollouts/bluegreen",
        f"{nome_lab}/manifests/istio",
        f"{nome_lab}/manifests/analysis",
        f"{nome_lab}/manifests/datadog",
        f"{nome_lab}/argocd",
        f"{nome_lab}/docs",
    ]

    for pasta in pastas:
        os.makedirs(pasta, exist_ok=True)
        print(f"[+] Diretório criado: {pasta}")

    # 1. Template do Argo Rollout com Canary + Istio + Analysis (base)
    rollout_canary_yaml = """apiVersion: argoproj.io/v1alpha1
kind: Rollout
metadata:
  name: app-canary
  namespace: gitops-lab
  annotations:
    notifications.argoproj.io/subscribe.on-rollout-completed.github: ""
    notifications.argoproj.io/subscribe.on-rollout-aborted.github: ""
spec:
  replicas: 4
  revisionHistoryLimit: 5
  selector:
    matchLabels:
      app: minha-aplicacao
      track: canary
  template:
    metadata:
      labels:
        app: minha-aplicacao
        track: canary
      annotations:
        sidecar.istio.io/inject: "true"
        # Exemplo de integração com Datadog APM/Logs
        ad.datadoghq.com/web.logs: '[{"source": "nodejs", "service": "minha-aplicacao"}]'
    spec:
      containers:
        - name: web
          image: ghcr.io/seu-org/minha-aplicacao:v1.0.0
          ports:
            - containerPort: 8080
          readinessProbe:
            httpGet:
              path: /healthz
              port: 8080
            initialDelaySeconds: 5
            periodSeconds: 5
          livenessProbe:
            httpGet:
              path: /livez
              port: 8080
            initialDelaySeconds: 10
            periodSeconds: 10
          resources:
            requests:
              memory: "256Mi"
              cpu: "250m"
            limits:
              memory: "512Mi"
              cpu: "500m"
  strategy:
    canary:
      trafficRouting:
        istio:
          virtualService:
            name: app-vs
            routes:
              - primary
      analysis:
        templates:
          - templateName: datadog-success-rate
        startingStep: 1
        args:
          - name: service-name
            value: minha-aplicacao
      steps:
        - setWeight: 5
        - pause: { duration: 2m }
        - analysis:
            templates:
              - templateName: datadog-success-rate
        - setWeight: 20
        - pause: { duration: 3m }
        - analysis:
            templates:
              - templateName: datadog-success-rate
        - setWeight: 50
        - pause: { duration: 5m }
        - analysis:
            templates:
              - templateName: datadog-success-rate
        - setWeight: 80
        - pause: { duration: 5m }
        - setWeight: 100
"""

    with open(f"{nome_lab}/manifests/rollouts/canary/rollout-canary.yaml", "w") as f:
        f.write(rollout_canary_yaml)

    # 2. Template do Argo Rollout com Blue/Green + Istio
    rollout_bg_yaml = """apiVersion: argoproj.io/v1alpha1
kind: Rollout
metadata:
  name: app-bluegreen
  namespace: gitops-lab
spec:
  replicas: 3
  revisionHistoryLimit: 3
  selector:
    matchLabels:
      app: minha-aplicacao-bg
  template:
    metadata:
      labels:
        app: minha-aplicacao-bg
      annotations:
        sidecar.istio.io/inject: "true"
    spec:
      containers:
        - name: web
          image: ghcr.io/seu-org/minha-aplicacao:v1.0.0
          ports:
            - containerPort: 8080
          resources:
            requests:
              memory: "256Mi"
              cpu: "250m"
            limits:
              memory: "512Mi"
              cpu: "500m"
  strategy:
    blueGreen:
      activeService: app-active
      previewService: app-preview
      autoPromotionEnabled: false
      scaleDownDelaySeconds: 30
      prePromotionAnalysis:
        templates:
          - templateName: datadog-success-rate
        args:
          - name: service-name
            value: minha-aplicacao-bg
      postPromotionAnalysis:
        templates:
          - templateName: datadog-success-rate
        args:
          - name: service-name
            value: minha-aplicacao-bg
"""

    with open(f"{nome_lab}/manifests/rollouts/bluegreen/rollout-bluegreen.yaml", "w") as f:
        f.write(rollout_bg_yaml)

    # 3. Istio VirtualService + DestinationRule (base para Canary com subset)
    istio_vs_dr_yaml = """apiVersion: networking.istio.io/v1beta1
kind: VirtualService
metadata:
  name: app-vs
  namespace: gitops-lab
spec:
  hosts:
    - minha-app.local
  gateways:
    - mesh
  http:
    - name: primary
      route:
        - destination:
            host: app-canary-stable
            subset: stable
          weight: 100
        - destination:
            host: app-canary-canary
            subset: canary
          weight: 0
---
apiVersion: networking.istio.io/v1beta1
kind: DestinationRule
metadata:
  name: app-dr
  namespace: gitops-lab
spec:
  host: app-canary-service
  subsets:
    - name: stable
      labels:
        app: minha-aplicacao
        rollouts-pod-template-hash: stable
    - name: canary
      labels:
        app: minha-aplicacao
        rollouts-pod-template-hash: canary
"""

    with open(f"{nome_lab}/manifests/istio/virtualservice-destinationrule.yaml", "w") as f:
        f.write(istio_vs_dr_yaml)

    # 4. AnalysisTemplate para Datadog (template base)
    analysis_datadog_yaml = """apiVersion: argoproj.io/v1alpha1
kind: AnalysisTemplate
metadata:
  name: datadog-success-rate
  namespace: gitops-lab
spec:
  args:
    - name: service-name
  metrics:
    - name: success-rate
      interval: 2m
      count: 3
      successCondition: result[0] >= 0.99
      failureLimit: 2
      provider:
        datadog:
          apiVersion: v1
          interval: 2m
          query: |
            sum:trace.servlet.request.hits{service:{{args.service-name}},env:lab}.as_count() - 
            sum:trace.servlet.request.errors{service:{{args.service-name}},env:lab}.as_count()
            /
            sum:trace.servlet.request.hits{service:{{args.service-name}},env:lab}.as_count()
"""

    with open(f"{nome_lab}/manifests/analysis/analysistemplate-datadog.yaml", "w") as f:
        f.write(analysis_datadog_yaml)

    # 5. ArgoCD Application (GitOps sync)
    argocd_app_yaml = """apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: gitops-lab-app
  namespace: argocd
spec:
  project: default
  source:
    repoURL: https://github.com/seu-usuario/seu-repo.git
    targetRevision: main
    path: gitops-lab-argo-istio/manifests
  destination:
    server: https://kubernetes.default.svc
    namespace: gitops-lab
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
    syncOptions:
      - CreateNamespace=true
"""

    with open(f"{nome_lab}/argocd/application.yaml", "w") as f:
        f.write(argocd_app_yaml)

    # 6. Workflow de Retorno / Notificação (GitHub Actions) - colocado na raiz .github/workflows conforme solicitado
    workflow_yaml = """name: GitOps Rollout Callback

on:
  repository_dispatch:
    types: [rollout-completed, rollout-aborted, rollout-paused]

jobs:
  report:
    runs-on: ubuntu-latest
    env:
      SHA: ${{ github.event.client_payload.sha }}
      EVENT: ${{ github.event.action }}
      ROLLOUT_NAME: ${{ github.event.client_payload.rollout }}
      NAMESPACE: ${{ github.event.client_payload.namespace }}
    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Notificar Status do Rollout
        run: |
          echo "==============================================="
          echo "GitOps Progressive Delivery - Rollout Callback"
          echo "==============================================="
          echo "Evento: $EVENT"
          echo "Rollout: $ROLLOUT_NAME"
          echo "Namespace: $NAMESPACE"
          echo "Commit SHA: $SHA"
          echo "==============================================="
"""

    # Garantir diretório .github/workflows na raiz do repo
    os.makedirs(".github/workflows", exist_ok=True)
    with open(".github/workflows/retorno-rollout.yml", "w") as f:
        f.write(workflow_yaml)
    print(f"[+] Workflow criado/atualizado em .github/workflows/retorno-rollout.yml")

    print(f"\n[Sucesso] Laboratório '{nome_lab}' gerado com Canary, Blue/Green, Istio, AnalysisTemplate (Datadog) e ArgoCD Application!")

if __name__ == "__main__":
    criar_estrutura_lab()