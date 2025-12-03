/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component, onWillStart, onMounted, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { rpc } from "@web/core/network/rpc";

/**
 * OneDesk Dashboard avec ApexCharts
 * Dashboard Principal avec graphiques interactifs, exports et auto-refresh
 */
export class OneDeskDashboard extends Component {
    setup() {
        this.orm = useService("orm");

        this.state = useState({
            loading: true,
            error: null,
            data: {},
            charts: {},
            autoRefresh: true,
            refreshInterval: 300000, // 5 minutes
        });

        onWillStart(async () => {
            await this.loadDashboardData();
        });

        onMounted(() => {
            this.initializeCharts();
            if (this.state.autoRefresh) {
                this.startAutoRefresh();
            }
        });
    }

    /**
     * Charger les données du dashboard
     */
    async loadDashboardData() {
        try {
            console.log("📊 Chargement des données du dashboard...");
            const response = await rpc("/onedesk/dashboard/main/data", {});
            console.log("📊 Réponse reçue:", response);

            if (response.status === "success") {
                this.state.data = response.data;
                this.state.loading = false;
                console.log("✅ Données chargées avec succès:", this.state.data);
            } else if (response.status === "error") {
                console.error("❌ Erreur backend:", response.message);
                this.state.loading = false;
                this.state.error = response.message;
            } else {
                console.error("❌ Réponse inattendue:", response);
                this.state.loading = false;
                this.state.error = "Réponse inattendue du serveur";
            }
        } catch (error) {
            console.error("❌ Erreur chargement dashboard:", error);
            this.state.loading = false;
            this.state.error = error.message || "Erreur de connexion";
        }
    }

    /**
     * Initialiser tous les graphiques ApexCharts
     */
    initializeCharts() {
        this.renderRevenueChart();
        this.renderReservationsChart();
        this.renderOccupancyGauge();
        this.renderPropertiesPieChart();
    }

    /**
     * Graphique 1: Évolution du Revenu (12 mois) - Ligne
     */
    renderRevenueChart() {
        const container = document.getElementById("revenue-chart");
        if (!container || !this.state.data.revenue_12_months) return;

        const data = this.state.data.revenue_12_months;

        const options = {
            series: [
                {
                    name: "Année Actuelle",
                    data: data.current_year || []
                },
                {
                    name: "Année Précédente",
                    data: data.previous_year || []
                }
            ],
            chart: {
                type: "line",
                height: 350,
                toolbar: {
                    show: true,
                    tools: {
                        download: true,
                        selection: true,
                        zoom: true,
                        zoomin: true,
                        zoomout: true,
                        pan: true,
                    }
                },
                animations: {
                    enabled: true,
                    easing: "easeinout",
                    speed: 800
                }
            },
            colors: ["#008FFB", "#00E396"],
            dataLabels: {
                enabled: false
            },
            stroke: {
                curve: "smooth",
                width: 3
            },
            xaxis: {
                categories: data.months || ["Jan", "Fév", "Mar", "Avr", "Mai", "Juin", "Juil", "Aoû", "Sep", "Oct", "Nov", "Déc"],
                title: {
                    text: "Mois"
                }
            },
            yaxis: {
                title: {
                    text: "Revenu (€)"
                },
                labels: {
                    formatter: function(value) {
                        return value.toLocaleString("fr-FR") + " €";
                    }
                }
            },
            tooltip: {
                y: {
                    formatter: function(value) {
                        return value.toLocaleString("fr-FR", {
                            style: "currency",
                            currency: "EUR"
                        });
                    }
                }
            },
            legend: {
                position: "top"
            },
            grid: {
                borderColor: "#e7e7e7",
                row: {
                    colors: ["#f3f3f3", "transparent"],
                    opacity: 0.5
                }
            }
        };

        this.state.charts.revenueChart = new ApexCharts(container, options);
        this.state.charts.revenueChart.render();
    }

    /**
     * Graphique 2: Réservations par Statut - Barre
     */
    renderReservationsChart() {
        const container = document.getElementById("reservations-chart");
        if (!container || !this.state.data.reservations_by_status) return;

        const data = this.state.data.reservations_by_status;

        const options = {
            series: [{
                name: "Réservations",
                data: data.counts || []
            }],
            chart: {
                type: "bar",
                height: 350,
                toolbar: {
                    show: true
                }
            },
            colors: ["#00E396", "#FEB019", "#008FFB", "#FF4560"],
            plotOptions: {
                bar: {
                    horizontal: false,
                    columnWidth: "55%",
                    distributed: true,
                    dataLabels: {
                        position: "top"
                    }
                }
            },
            dataLabels: {
                enabled: true,
                offsetY: -20,
                style: {
                    fontSize: "12px",
                    colors: ["#304758"]
                }
            },
            xaxis: {
                categories: data.statuses || ["Confirmée", "En attente", "Complétée", "Annulée"],
                title: {
                    text: "Statut"
                }
            },
            yaxis: {
                title: {
                    text: "Nombre de Réservations"
                }
            },
            legend: {
                show: false
            },
            tooltip: {
                y: {
                    formatter: function(value) {
                        return value + " réservations";
                    }
                }
            }
        };

        this.state.charts.reservationsChart = new ApexCharts(container, options);
        this.state.charts.reservationsChart.render();
    }

    /**
     * Graphique 3: Taux d'Occupation - Jauge (Radial Bar)
     */
    renderOccupancyGauge() {
        const container = document.getElementById("occupancy-gauge");
        if (!container || this.state.data.occupancy_rate === undefined || this.state.data.occupancy_rate === null) return;

        const occupancyRate = this.state.data.occupancy_rate;

        const options = {
            series: [occupancyRate],
            chart: {
                type: "radialBar",
                height: 350
            },
            plotOptions: {
                radialBar: {
                    hollow: {
                        size: "70%"
                    },
                    dataLabels: {
                        name: {
                            fontSize: "22px",
                            offsetY: -10
                        },
                        value: {
                            fontSize: "36px",
                            formatter: function(val) {
                                return val.toFixed(1) + "%";
                            }
                        }
                    },
                    track: {
                        background: "#f2f2f2"
                    }
                }
            },
            colors: [occupancyRate < 60 ? "#FF4560" : occupancyRate < 80 ? "#FEB019" : "#00E396"],
            labels: ["Taux d'Occupation"],
            fill: {
                type: "gradient",
                gradient: {
                    shade: "dark",
                    type: "vertical",
                    gradientToColors: [occupancyRate < 60 ? "#D32F2F" : occupancyRate < 80 ? "#F57C00" : "#388E3C"],
                    stops: [0, 100]
                }
            }
        };

        this.state.charts.occupancyGauge = new ApexCharts(container, options);
        this.state.charts.occupancyGauge.render();
    }

    /**
     * Graphique 4: Distribution des Propriétés par Type - Camembert
     */
    renderPropertiesPieChart() {
        const container = document.getElementById("properties-pie");
        if (!container || !this.state.data.properties_by_city) return;

        const data = this.state.data.properties_by_city;

        const options = {
            series: data.counts || [],
            chart: {
                type: "donut",
                height: 350
            },
            labels: data.cities || [],
            colors: ["#008FFB", "#00E396", "#FEB019", "#FF4560", "#775DD0"],
            legend: {
                position: "bottom"
            },
            dataLabels: {
                enabled: true,
                formatter: function(val, opts) {
                    return opts.w.config.series[opts.seriesIndex];
                }
            },
            plotOptions: {
                pie: {
                    donut: {
                        size: "65%",
                        labels: {
                            show: true,
                            total: {
                                show: true,
                                label: "Total Propriétés",
                                formatter: function(w) {
                                    return w.globals.seriesTotals.reduce((a, b) => a + b, 0);
                                }
                            }
                        }
                    }
                }
            },
            tooltip: {
                y: {
                    formatter: function(value) {
                        return value + " propriétés";
                    }
                }
            }
        };

        this.state.charts.propertiesPie = new ApexCharts(container, options);
        this.state.charts.propertiesPie.render();
    }

    /**
     * Rafraîchir tous les graphiques
     */
    async refreshDashboard() {
        // Détruire les graphiques existants d'abord
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
        await this.loadDashboardData();

        // Si pas d'erreur, réinitialiser les graphiques
        if (!this.state.error) {
            // Utiliser nextTick pour s'assurer que le DOM est mis à jour
            setTimeout(() => {
                this.initializeCharts();
            }, 100);
        }
    }

    /**
     * Démarrer le rafraîchissement automatique
     */
    startAutoRefresh() {
        if (this.refreshTimer) {
            clearInterval(this.refreshTimer);
        }

        this.refreshTimer = setInterval(() => {
            if (this.state.autoRefresh) {
                this.refreshDashboard();
            }
        }, this.state.refreshInterval);
    }

    /**
     * Exporter les données en Excel
     */
    async exportToExcel() {
        try {
            const response = await rpc("/onedesk/dashboard/export/excel", {});
            if (response.file_url) {
                window.location.href = response.file_url;
            }
        } catch (error) {
            console.error("Erreur export Excel:", error);
        }
    }

    /**
     * Exporter le dashboard en PDF
     */
    async exportToPDF() {
        try {
            const response = await rpc("/onedesk/dashboard/export/pdf", {});
            if (response.file_url) {
                window.location.href = response.file_url;
            }
        } catch (error) {
            console.error("Erreur export PDF:", error);
        }
    }

    /**
     * Télécharger un graphique en PNG
     */
    downloadChartPNG(chartName) {
        const chart = this.state.charts[chartName];
        if (chart && chart.dataURI) {
            chart.dataURI().then(({ imgURI }) => {
                const link = document.createElement("a");
                link.href = imgURI;
                link.download = `${chartName}.png`;
                link.click();
            });
        }
    }
}

OneDeskDashboard.template = "onedesk_core.DashboardMain";

registry.category("actions").add("onedesk_dashboard_main", OneDeskDashboard);
