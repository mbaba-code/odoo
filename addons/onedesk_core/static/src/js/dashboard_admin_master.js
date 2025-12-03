/** @odoo-module **/

import { Component, onMounted, onWillUnmount, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { rpc } from "@web/core/network/rpc";

/**
 * Dashboard Admin Master - Vue globale pour Master Admin
 * Affiche toutes les métriques multi-tenant (toutes les companies)
 */
class DashboardAdminMaster extends Component {
    static template = "onedesk_core.DashboardAdminMaster";

    setup() {
        this.state = useState({
            loading: true,
            error: null,
            data: {},
            charts: {},
        });

        onMounted(() => {
            this.loadAdminData();
        });

        onWillUnmount(() => {
            // Nettoyer les graphiques lors de la destruction
            Object.values(this.state.charts).forEach(chart => {
                if (chart && chart.destroy) {
                    chart.destroy();
                }
            });
        });
    }

    /**
     * Charge les données admin depuis le backend
     */
    async loadAdminData() {
        try {
            console.log("👑 Chargement des données Admin Master...");
            const response = await rpc("/onedesk/dashboard/admin/data", {});
            console.log("👑 Réponse reçue:", response);

            if (response.status === "success") {
                this.state.data = response.data;
                this.state.loading = false;
                console.log("✅ Données admin chargées:", this.state.data);

                // Initialiser les graphiques après le chargement
                setTimeout(() => {
                    this.initializeCharts();
                }, 100);
            } else if (response.status === "error") {
                console.error("❌ Erreur backend:", response.message);
                this.state.loading = false;
                this.state.error = response.message;
            }
        } catch (error) {
            console.error("❌ Erreur chargement admin dashboard:", error);
            this.state.loading = false;
            this.state.error = error.message || "Erreur de connexion";
        }
    }

    /**
     * Initialise tous les graphiques ApexCharts
     */
    initializeCharts() {
        this.createRevenueByCompanyChart();
        this.createCompaniesStatusChart();
        this.createGlobalRevenueChart();
        this.createReservationsChart();
    }

    /**
     * Graphique: Revenus par Company
     */
    createRevenueByCompanyChart() {
        const container = document.getElementById("revenue-by-company-chart");
        if (!container || !this.state.data.revenue_by_company) return;

        const data = this.state.data.revenue_by_company;

        const options = {
            series: [{
                name: 'Revenu Total',
                data: data.revenues || []
            }],
            chart: {
                type: 'bar',
                height: 350,
                toolbar: {
                    show: true,
                    tools: {
                        download: true,
                        selection: false,
                        zoom: false,
                        zoomin: false,
                        zoomout: false,
                        pan: false,
                        reset: false
                    }
                }
            },
            plotOptions: {
                bar: {
                    borderRadius: 8,
                    horizontal: false,
                    columnWidth: '60%',
                    dataLabels: {
                        position: 'top',
                    },
                }
            },
            dataLabels: {
                enabled: true,
                formatter: function (val) {
                    return val.toLocaleString('fr-FR', {style: 'currency', currency: 'EUR'});
                },
                offsetY: -20,
                style: {
                    fontSize: '11px',
                    colors: ["#304758"]
                }
            },
            xaxis: {
                categories: data.companies || [],
                labels: {
                    style: {
                        fontSize: '12px'
                    }
                }
            },
            yaxis: {
                title: {
                    text: 'Revenu (€)'
                },
                labels: {
                    formatter: function (val) {
                        return val.toLocaleString('fr-FR', {style: 'currency', currency: 'EUR'});
                    }
                }
            },
            colors: ['#1e40af'],
            title: {
                text: 'Revenus par Company',
                align: 'center',
                style: {
                    fontSize: '16px',
                    fontWeight: 'bold'
                }
            },
            grid: {
                borderColor: '#e7e7e7',
                row: {
                    colors: ['#f9fafb', 'transparent'],
                    opacity: 0.5
                },
            }
        };

        this.state.charts.revenueByCompany = new ApexCharts(container, options);
        this.state.charts.revenueByCompany.render();
    }

    /**
     * Graphique: Statut des Companies (Actives/Inactives)
     */
    createCompaniesStatusChart() {
        const container = document.getElementById("companies-status-chart");
        if (!container || !this.state.data.companies_status) return;

        const data = this.state.data.companies_status;

        const options = {
            series: data.counts || [],
            chart: {
                type: 'donut',
                height: 300
            },
            labels: data.labels || [],
            colors: ['#059669', '#dc2626'],
            legend: {
                position: 'bottom'
            },
            dataLabels: {
                enabled: true,
                formatter: function (val, opts) {
                    return opts.w.config.series[opts.seriesIndex];
                }
            },
            plotOptions: {
                pie: {
                    donut: {
                        size: '65%',
                        labels: {
                            show: true,
                            total: {
                                show: true,
                                label: 'Total',
                                fontSize: '16px',
                                fontWeight: 600
                            }
                        }
                    }
                }
            },
            title: {
                text: 'Companies par Statut',
                align: 'center',
                style: {
                    fontSize: '16px',
                    fontWeight: 'bold'
                }
            }
        };

        this.state.charts.companiesStatus = new ApexCharts(container, options);
        this.state.charts.companiesStatus.render();
    }

    /**
     * Graphique: Évolution Revenus Globaux (12 mois)
     */
    createGlobalRevenueChart() {
        const container = document.getElementById("global-revenue-chart");
        if (!container || !this.state.data.global_revenue_12_months) return;

        const data = this.state.data.global_revenue_12_months;

        const options = {
            series: [{
                name: 'Année en cours',
                data: data.current_year || []
            }, {
                name: 'Année précédente',
                data: data.previous_year || []
            }],
            chart: {
                type: 'area',
                height: 350,
                toolbar: {
                    show: true
                },
                animations: {
                    enabled: true,
                    easing: 'easeinout',
                    speed: 800
                }
            },
            dataLabels: {
                enabled: false
            },
            stroke: {
                curve: 'smooth',
                width: 2
            },
            xaxis: {
                categories: data.months || [],
                labels: {
                    style: {
                        fontSize: '12px'
                    }
                }
            },
            yaxis: {
                title: {
                    text: 'Revenu (€)'
                },
                labels: {
                    formatter: function (val) {
                        return val.toLocaleString('fr-FR', {style: 'currency', currency: 'EUR'});
                    }
                }
            },
            colors: ['#3b82f6', '#94a3b8'],
            fill: {
                type: 'gradient',
                gradient: {
                    shadeIntensity: 1,
                    opacityFrom: 0.7,
                    opacityTo: 0.2,
                }
            },
            legend: {
                position: 'top',
                horizontalAlign: 'right'
            },
            title: {
                text: 'Évolution Revenus Globaux (12 mois)',
                align: 'center',
                style: {
                    fontSize: '16px',
                    fontWeight: 'bold'
                }
            },
            grid: {
                borderColor: '#e7e7e7'
            },
            tooltip: {
                y: {
                    formatter: function (val) {
                        return val.toLocaleString('fr-FR', {style: 'currency', currency: 'EUR'});
                    }
                }
            }
        };

        this.state.charts.globalRevenue = new ApexCharts(container, options);
        this.state.charts.globalRevenue.render();
    }

    /**
     * Graphique: Réservations Actives par Company
     */
    createReservationsChart() {
        const container = document.getElementById("reservations-by-company-chart");
        if (!container || !this.state.data.reservations_by_company) return;

        const data = this.state.data.reservations_by_company;

        const options = {
            series: [{
                name: 'Réservations Actives',
                data: data.counts || []
            }],
            chart: {
                type: 'bar',
                height: 350,
                toolbar: {
                    show: true
                }
            },
            plotOptions: {
                bar: {
                    borderRadius: 6,
                    horizontal: true,
                    dataLabels: {
                        position: 'top',
                    },
                }
            },
            dataLabels: {
                enabled: true,
                offsetX: 30,
                style: {
                    fontSize: '12px',
                    colors: ['#304758']
                }
            },
            xaxis: {
                categories: data.companies || [],
            },
            yaxis: {
                title: {
                    text: 'Nombre de Réservations'
                }
            },
            colors: ['#0891b2'],
            title: {
                text: 'Réservations Actives par Company',
                align: 'center',
                style: {
                    fontSize: '16px',
                    fontWeight: 'bold'
                }
            },
            grid: {
                borderColor: '#e7e7e7'
            }
        };

        this.state.charts.reservationsByCompany = new ApexCharts(container, options);
        this.state.charts.reservationsByCompany.render();
    }

    /**
     * Rafraîchir le dashboard
     */
    async refreshDashboard() {
        // Détruire les graphiques existants
        Object.values(this.state.charts).forEach(chart => {
            if (chart && chart.destroy) {
                chart.destroy();
            }
        });
        this.state.charts = {};

        // Activer le loader
        this.state.loading = true;
        this.state.error = null;

        // Recharger les données
        await this.loadAdminData();
    }

    /**
     * Export Excel
     */
    async exportToExcel() {
        try {
            const response = await rpc("/onedesk/dashboard/admin/export/excel", {});

            if (response.status === "success") {
                // Télécharger le fichier
                const link = document.createElement('a');
                link.href = `/web/content/${response.attachment_id}?download=true`;
                link.download = response.filename;
                link.click();
            } else {
                alert("Erreur lors de l'export Excel: " + response.message);
            }
        } catch (error) {
            console.error("Erreur export Excel:", error);
            alert("Erreur lors de l'export Excel");
        }
    }

    /**
     * Export PDF
     */
    async exportToPDF() {
        try {
            const response = await rpc("/onedesk/dashboard/admin/export/pdf", {});

            if (response.status === "success") {
                // Télécharger le fichier
                const link = document.createElement('a');
                link.href = `/web/content/${response.attachment_id}?download=true`;
                link.download = response.filename;
                link.click();
            } else {
                alert("Erreur lors de l'export PDF: " + response.message);
            }
        } catch (error) {
            console.error("Erreur export PDF:", error);
            alert("Erreur lors de l'export PDF");
        }
    }
}

// Enregistrer le composant comme action client
registry.category("actions").add("onedesk_dashboard_admin_master", DashboardAdminMaster);

export default DashboardAdminMaster;
