# 🎯 SPECIFICAÇÃO: Corporate Microlearning Platform

## Redefinição Estratégica

**De:** General-purpose LMS (micro-learning-platform)  
**Para:** Corporate Microlearning SaaS (MicroLearn Pro)

---

## 📊 Análise de Impacto

| Métrica | Antes | Depois |
|---------|-------|--------|
| **Mercado** | $18B LMS genérico | $380B Corporate Training |
| **Receita/user/mês** | $0 (free) | $5-50 (B2B) |
| **Stickiness** | Baixa | Alta (HR integration) |
| **Barreira entrada** | Zero | Integração + Compliance |
| **Concorrência** | Alta (Duolingo, Khan) | Média (Docebo, Centrical) |

---

## 🎯 Produto Alvo

**Nome:** MicroLearn Pro  
**Target:** PMEs e Departamentos de RH/Training  
**Preço:** €5-50/user/mês  
**Diferenciador:** AI-powered microlearning + simples de usar

---

## 🏗️ Arquitetura Redefinida

### Módulos Principais

| Módulo | Descrição | Prioridade |
|--------|-----------|------------|
| **Employee Portal** | Dashboard personal para employees | 🔴 Alta |
| **Admin Panel** | Gestão de cursos, users, reports | 🔴 Alta |
| **AI Recommender** | Recomendação automática de conteúdo | 🔴 Alta |
| **Progress Tracker** | Tracking de completion, certifications | 🔴 Alta |
| **HR Integration** | API for Workday, SAP, HR systems | 🟠 Média |
| **Compliance** | Certificações obrigatórias | 🟠 Média |
| **Analytics** | Reports ROI, effectiveness | 🟠 Média |
| **Mobile** | PWA para acesso mobile | 🟡 Baixa |

### Features Diferenciadoras

1. **AI Microlearning** - Conteúdo sugerido baseado em role/goals
2. **5-min lessons** - Formato ideal para trabalho
3. **Slack/Teams integration** - Notificações inline
4. **Compliance tracking** - Mandatory training automatic
5. **Gamificação ringan** - Badges, não complexo

---

## 📱 UI/UX Simplified

### Employee View
- Dashboard com "Today's micro-lesson"
- Progresso semanal
- Badges earned
- Recommended next course

### Admin View
- Criar curso em 5 minutos
- Upload CSV employees
- Ver reports de compliance
- Export analytics

---

## 🔧 Stack Tecnológico

- **Backend:** Flask (já temos) → manter
- **Frontend:** React/Vue (atual: Jinja2) → migrar para PWA
- **Database:** SQLite → PostgreSQL (produção)
- **AI:** OpenAI API para recommendations
- **Auth:** JWT + SSO (SAML/OIDC)

---

## 🚀 Roadmap de Implementação

### Fase 1 (Semana 1-2): Core
- [ ] Redefinir modelos de dados para multi-tenant
- [ ] Employee vs Admin roles
- [ ] Dashboard simplificado
- [ ] Basic progress tracking

### Fase 2 (Semana 3-4): AI Features
- [ ] AI content recommendations
- [ ] Personalized learning paths
- [ ] Smart notifications

### Fase 3 (Semana 5-6): Integration
- [ ] REST API pública
- [ ] Webhook para HR systems
- [ ] SSO (Google, Microsoft)

### Fase 4 (Semana 7-8): Enterprise
- [ ] Compliance certificates
- [ ] Advanced analytics
- [ ] White-label option

---

## 💰 Modelo de Negócio

| Tier | Preço | Features |
|------|-------|----------|
| **Starter** | €5/user | 50 employees, basic courses |
| **Pro** | €15/user | Unlimited, AI, analytics |
| **Enterprise** | €50/user | White-label, SSO, API |

---

## 📊 KPIs Success

- Employee completion rate: >80%
- Time to complete course: <5 min/day
- Customer retention: >90%/year
- NPS: >50

---

## 🎯 Próximos Passos

1. Atualizar README com nova visão
2. Criar spec detalhada para cada módulo
3. Implementar Employee Portal
4. Adicionar AI recommendations
5. Desenvolver API

---

*Documento criado: 2026-03-28*  
*Versão: 1.0 - B2B Corporate Pivot*