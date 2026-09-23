"""
Script to generate realistic AUTOSAR High-Level Design (HLD) sample PDF documents
for the AUTOSAR HLD Document Analysis Assistant demo.

Generates:
1. sample_autosar_hld_v1.pdf - Baseline document with intentional architectural flaws.
2. sample_autosar_hld_v2.pdf - Revised document resolving flaws and adding LaneKeepAssistSWC.
"""

import os
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    PageBreak,
    KeepTogether,
    HRFlowable
)


def create_header_footer(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(colors.HexColor("#718096"))
    # Header
    canvas.drawString(
        54, 11 * inch - 36,
        "Tata Technologies | Automotive AI Platform — AUTOSAR High-Level Architecture Design"
    )
    canvas.setStrokeColor(colors.HexColor("#CBD5E0"))
    canvas.setLineWidth(0.5)
    canvas.line(54, 11 * inch - 42, 8.5 * inch - 54, 11 * inch - 42)

    # Footer
    page_num = canvas.getPageNumber()
    canvas.line(54, 46, 8.5 * inch - 54, 46)
    canvas.drawString(
        54, 34,
        "CONFIDENTIAL — DEMONSTRATION ARTIFACT ONLY — AUTOSAR 4.4 CLASSICAL ARCHITECTURE"
    )
    canvas.drawRightString(
        8.5 * inch - 54, 34,
        f"Page {page_num}"
    )
    canvas.restoreState()


def build_v1_pdf(output_path: str):
    doc = SimpleDocTemplate(
        output_path,
        pagesize=letter,
        leftMargin=54,
        rightMargin=54,
        topMargin=54,
        bottomMargin=54
    )

    styles = getSampleStyleSheet()

    # Custom styles
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=20,
        leading=24,
        textColor=colors.HexColor('#1A365D'),
        spaceAfter=6
    )

    subtitle_style = ParagraphStyle(
        'DocSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=11,
        leading=15,
        textColor=colors.HexColor('#4A5568'),
        spaceAfter=12
    )

    h1_style = ParagraphStyle(
        'SectionH1',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=13,
        leading=17,
        textColor=colors.HexColor('#2B6CB0'),
        spaceBefore=12,
        spaceAfter=6
    )

    h2_style = ParagraphStyle(
        'SectionH2',
        parent=styles['Heading3'],
        fontName='Helvetica-Bold',
        fontSize=10.5,
        leading=14,
        textColor=colors.HexColor('#2D3748'),
        spaceBefore=8,
        spaceAfter=4
    )

    body_style = ParagraphStyle(
        'BodyTextCustom',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=13,
        textColor=colors.HexColor('#2D3748'),
        spaceAfter=6
    )

    callout_style = ParagraphStyle(
        'CalloutText',
        parent=styles['Normal'],
        fontName='Helvetica-Oblique',
        fontSize=8.5,
        leading=12,
        textColor=colors.HexColor('#742A2A'),
        spaceAfter=4
    )

    table_header_style = ParagraphStyle(
        'TableHeader',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8,
        leading=10,
        textColor=colors.white
    )

    table_cell_style = ParagraphStyle(
        'TableCell',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8,
        leading=11,
        textColor=colors.HexColor('#1A202C')
    )

    story = []

    # Title & Metadata block
    story.append(Paragraph("AUTOSAR High-Level Design (HLD) Specification", title_style))
    story.append(Paragraph("Domain: Powertrain & Chassis Control Domain | Release 1.0 (Baseline)", subtitle_style))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor('#2B6CB0'), spaceAfter=10))

    meta_data = [
        [Paragraph("<b>Document ID:</b> DOC-AUTOSAR-PT-V1", table_cell_style),
         Paragraph("<b>Target ECU:</b> TriCore TC397x (Domain Controller)", table_cell_style)],
        [Paragraph("<b>Standard:</b> AUTOSAR Classic Platform 4.4.0", table_cell_style),
         Paragraph("<b>Classification:</b> ASIL-D / ISO 26262", table_cell_style)],
        [Paragraph("<b>Author:</b> Powertrain Architecture Guild", table_cell_style),
         Paragraph("<b>Release Date:</b> 2026-03-15", table_cell_style)],
    ]
    meta_table = Table(meta_data, colWidths=[250, 250])
    meta_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#EDF2F7')),
        ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E0')),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    story.append(meta_table)
    story.append(Spacer(1, 12))

    # Section 1: Architectural Overview
    story.append(Paragraph("1. System Architecture Overview", h1_style))
    story.append(Paragraph(
        "This High-Level Design (HLD) document specifies the software architecture for the Powertrain and Chassis "
        "Domain Controller in compliance with AUTOSAR Classic Release 4.4. The architecture defines application "
        "software components (SWCs), sender-receiver and client-server interfaces, port prototypes, signal mapping, "
        "and data type definitions necessary for distributed torque control and regenerative braking coordination.",
        body_style
    ))

    # Section 2: Software Component Specification - BrakeControlSWC
    story.append(Paragraph("2. Software Component: BrakeControlSWC", h1_style))
    story.append(Paragraph(
        "<b>Component Type:</b> Application Software Component (ApplicationSWC)<br/>"
        "<b>Execution Periodicity:</b> 10ms (Cyclic Runnable: <code>BrakeControl_Runnable_10ms</code>)<br/>"
        "<b>Safety Level:</b> ASIL-D<br/>"
        "<b>Description:</b> Responsible for calculating total friction and regenerative braking demand based on "
        "driver brake pedal input, wheel speed sensor feedback, and vehicle dynamic stability.",
        body_style
    ))

    story.append(Paragraph("Ports & Interface Definitions for BrakeControlSWC:", h2_style))
    bc_ports = [
        [Paragraph("Port Name", table_header_style), Paragraph("Port Type", table_header_style),
         Paragraph("Interface Name", table_header_style), Paragraph("Signal / Element", table_header_style),
         Paragraph("Data Type", table_header_style), Paragraph("Target / Provider", table_header_style)],
        [Paragraph("RPort_VehicleSpeed", table_cell_style), Paragraph("R-Port (Require)", table_cell_style),
         Paragraph("If_VehicleSpeed", table_cell_style), Paragraph("VehicleSpeed_kph", table_cell_style),
         Paragraph("float32", table_cell_style), Paragraph("WheelSpeedSensorSWC", table_cell_style)],
        [Paragraph("PPort_BrakeTorqueRequest", table_cell_style), Paragraph("P-Port (Provide)", table_cell_style),
         Paragraph("If_BrakeTorque", table_cell_style), Paragraph("BrakeTorque_Nm", table_cell_style),
         Paragraph("uint16", table_cell_style), Paragraph("EngineManagerSWC", table_cell_style)],
        [Paragraph("RPort_SteeringAngle", table_cell_style), Paragraph("R-Port (Require)", table_cell_style),
         Paragraph("If_SteeringAngle", table_cell_style), Paragraph("SteeringAngle_deg", table_cell_style),
         Paragraph("float32", table_cell_style), Paragraph("SteeringAngleSensorSWC", table_cell_style)],
    ]
    t_bc = Table(bc_ports, colWidths=[95, 75, 80, 85, 55, 110])
    t_bc.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2B6CB0')),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E0')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F7FAFC')]),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
    ]))
    story.append(t_bc)
    story.append(Spacer(1, 8))

    # Page Break for Page 2
    story.append(PageBreak())

    # Section 3: Software Component: EngineManagerSWC
    story.append(Paragraph("3. Software Component: EngineManagerSWC", h1_style))
    story.append(Paragraph(
        "<b>Component Type:</b> Application Software Component (ApplicationSWC)<br/>"
        "<b>Execution Periodicity:</b> 5ms (Cyclic Runnable: <code>EngineManager_Step_5ms</code>)<br/>"
        "<b>Safety Level:</b> ASIL-B<br/>"
        "<b>Description:</b> Controls primary combustion and e-motor drive torque synthesis, throttle response, "
        "and coordinates torque reduction commands received from chassis safety components during stability interventions.",
        body_style
    ))

    story.append(Paragraph("Ports & Interface Definitions for EngineManagerSWC:", h2_style))
    em_ports = [
        [Paragraph("Port Name", table_header_style), Paragraph("Port Type", table_header_style),
         Paragraph("Interface Name", table_header_style), Paragraph("Signal / Element", table_header_style),
         Paragraph("Data Type", table_header_style), Paragraph("Target / Provider", table_header_style)],
        [Paragraph("RPort_BrakeTorque", table_cell_style), Paragraph("R-Port (Require)", table_cell_style),
         Paragraph("If_BrakeTorque", table_cell_style), Paragraph("BrakeTorque_Nm", table_cell_style),
         Paragraph("uint16", table_cell_style), Paragraph("BrakeControlSWC", table_cell_style)],
        [Paragraph("PPort_EngineSpeed", table_cell_style), Paragraph("P-Port (Provide)", table_cell_style),
         Paragraph("If_EngineSpeed", table_cell_style), Paragraph("EngineSpeed_rpm", table_cell_style),
         Paragraph("uint16", table_cell_style), Paragraph("TransmissionControlSWC", table_cell_style)],
        [Paragraph("RPort_ThrottleDemand", table_cell_style), Paragraph("R-Port (Require)", table_cell_style),
         Paragraph("If_ThrottleDemand", table_cell_style), Paragraph("ThrottlePercent", table_cell_style),
         Paragraph("uint8", table_cell_style), Paragraph("PedalInterfaceSWC", table_cell_style)],
    ]
    t_em = Table(em_ports, colWidths=[95, 75, 80, 85, 55, 110])
    t_em.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2B6CB0')),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E0')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F7FAFC')]),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
    ]))
    story.append(t_em)
    story.append(Spacer(1, 10))

    # Section 4: Software Component: BatteryManagementSWC
    story.append(Paragraph("4. Software Component: BatteryManagementSWC", h1_style))
    story.append(Paragraph(
        "<b>Component Type:</b> Sensor/Actuator Software Component (SensorActuatorSWC)<br/>"
        "<b>Execution Periodicity:</b> 50ms (Cyclic Runnable: <code>BMS_Main_50ms</code>)<br/>"
        "<b>Safety Level:</b> ASIL-C<br/>"
        "<b>Description:</b> Monitors high-voltage battery pack State of Charge (SOC), State of Health (SOH), "
        "pack terminal voltage, and maximum discharge current limits.",
        body_style
    ))

    bms_ports = [
        [Paragraph("Port Name", table_header_style), Paragraph("Port Type", table_header_style),
         Paragraph("Interface Name", table_header_style), Paragraph("Signal / Element", table_header_style),
         Paragraph("Data Type", table_header_style), Paragraph("Target / Provider", table_header_style)],
        [Paragraph("PPort_BatterySOC", table_cell_style), Paragraph("P-Port (Provide)", table_cell_style),
         Paragraph("If_BatteryStatus", table_cell_style), Paragraph("BatterySOC_pct", table_cell_style),
         Paragraph("uint8", table_cell_style), Paragraph("TransmissionControlSWC", table_cell_style)],
        [Paragraph("PPort_BatteryCurrent", table_cell_style), Paragraph("P-Port (Provide)", table_cell_style),
         Paragraph("If_BatteryCurrent", table_cell_style), Paragraph("Current_A", table_cell_style),
         Paragraph("uint16", table_cell_style), Paragraph("TransmissionControlSWC", table_cell_style)],
    ]
    t_bms = Table(bms_ports, colWidths=[95, 75, 80, 85, 55, 110])
    t_bms.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2B6CB0')),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E0')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F7FAFC')]),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
    ]))
    story.append(t_bms)
    story.append(Spacer(1, 10))

    # Page Break for Page 3
    story.append(PageBreak())

    # Section 5: Software Component: TransmissionControlSWC
    story.append(Paragraph("5. Software Component: TransmissionControlSWC", h1_style))
    story.append(Paragraph(
        "<b>Component Type:</b> Application Software Component (ApplicationSWC)<br/>"
        "<b>Execution Periodicity:</b> 20ms (Cyclic Runnable: <code>TCU_Control_20ms</code>)<br/>"
        "<b>Safety Level:</b> ASIL-C<br/>"
        "<b>Description:</b> Controls automated dual-clutch transmission gear selection, clutch engagement schedules, "
        "and hybrid drive mode coupling based on engine speed and battery charge thresholds.",
        body_style
    ))

    tcu_ports = [
        [Paragraph("Port Name", table_header_style), Paragraph("Port Type", table_header_style),
         Paragraph("Interface Name", table_header_style), Paragraph("Signal / Element", table_header_style),
         Paragraph("Data Type", table_header_style), Paragraph("Target / Provider", table_header_style)],
        [Paragraph("RPort_EngineSpeed", table_cell_style), Paragraph("R-Port (Require)", table_cell_style),
         Paragraph("If_EngineSpeed", table_cell_style), Paragraph("EngineSpeed_rpm", table_cell_style),
         Paragraph("uint16", table_cell_style), Paragraph("EngineManagerSWC", table_cell_style)],
        [Paragraph("RPort_BatteryCurrent", table_cell_style), Paragraph("R-Port (Require)", table_cell_style),
         Paragraph("If_BatteryCurrent", table_cell_style), Paragraph("Current_A", table_cell_style),
         Paragraph("float32", table_cell_style), Paragraph("BatteryManagementSWC", table_cell_style)],
        [Paragraph("PPort_GearPosition", table_cell_style), Paragraph("P-Port (Provide)", table_cell_style),
         Paragraph("If_GearStatus", table_cell_style), Paragraph("CurrentGear", table_cell_style),
         Paragraph("uint8", table_cell_style), Paragraph("InstrumentClusterSWC", table_cell_style)],
    ]
    t_tcu = Table(tcu_ports, colWidths=[95, 75, 80, 85, 55, 110])
    t_tcu.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2B6CB0')),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E0')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F7FAFC')]),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
    ]))
    story.append(t_tcu)
    story.append(Spacer(1, 10))

    # Section 6: Functional Flows & Inter-Component Dependencies
    story.append(Paragraph("6. Functional Flows & End-to-End Traces", h1_style))
    story.append(Paragraph(
        "<b>Flow 1: Regenerative Braking Coordination</b><br/>"
        "1. <code>BrakeControlSWC</code> receives wheel speeds via <code>RPort_VehicleSpeed</code>.<br/>"
        "2. <code>BrakeControlSWC</code> computes negative torque command and emits <code>PPort_BrakeTorqueRequest</code>.<br/>"
        "3. <code>EngineManagerSWC</code> receives torque demand and reduces internal combustion output.<br/>"
        "4. <code>TransmissionControlSWC</code> commands optimal gear ratio for regenerative recovery.",
        body_style
    ))
    story.append(Paragraph(
        "<b>Flow 2: High Voltage Battery Overcurrent Protection</b><br/>"
        "1. <code>BatteryManagementSWC</code> samples pack current via <code>PPort_BatteryCurrent</code>.<br/>"
        "2. <code>TransmissionControlSWC</code> reads current via <code>RPort_BatteryCurrent</code> to modulate hybrid motor load.",
        body_style
    ))
    story.append(Spacer(1, 8))

    # Section 7: Data Types Summary
    story.append(Paragraph("7. Standard Data Type Definitions", h1_style))
    dt_rows = [
        [Paragraph("Data Type", table_header_style), Paragraph("Base Type", table_header_style),
         Paragraph("Unit", table_header_style), Paragraph("Resolution / Range", table_header_style)],
        [Paragraph("VehicleSpeed_kph", table_cell_style), Paragraph("float32", table_cell_style),
         Paragraph("km/h", table_cell_style), Paragraph("0.01 resolution (0.0 to 350.0)", table_cell_style)],
        [Paragraph("BrakeTorque_Nm", table_cell_style), Paragraph("uint16", table_cell_style),
         Paragraph("Nm", table_cell_style), Paragraph("1.0 resolution (0 to 65535)", table_cell_style)],
        [Paragraph("EngineSpeed_rpm", table_cell_style), Paragraph("uint16", table_cell_style),
         Paragraph("rpm", table_cell_style), Paragraph("1.0 resolution (0 to 12000)", table_cell_style)],
        [Paragraph("Current_A", table_cell_style), Paragraph("uint16", table_cell_style),
         Paragraph("Amperes", table_cell_style), Paragraph("0.1 resolution (-500 to +500)", table_cell_style)],
        [Paragraph("BatterySOC_pct", table_cell_style), Paragraph("uint8", table_cell_style),
         Paragraph("%", table_cell_style), Paragraph("1% (0 to 100)", table_cell_style)],
    ]
    t_dt = Table(dt_rows, colWidths=[120, 90, 80, 210])
    t_dt.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2B6CB0')),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E0')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F7FAFC')]),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
    ]))
    story.append(t_dt)

    doc.build(story, onFirstPage=create_header_footer, onLaterPages=create_header_footer)
    print(f"Generated sample HLD V1 at {output_path}")


def build_v2_pdf(output_path: str):
    doc = SimpleDocTemplate(
        output_path,
        pagesize=letter,
        leftMargin=54,
        rightMargin=54,
        topMargin=54,
        bottomMargin=54
    )

    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=20,
        leading=24,
        textColor=colors.HexColor('#1A365D'),
        spaceAfter=6
    )

    subtitle_style = ParagraphStyle(
        'DocSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=11,
        leading=15,
        textColor=colors.HexColor('#2E7D32'),
        spaceAfter=12
    )

    h1_style = ParagraphStyle(
        'SectionH1',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=13,
        leading=17,
        textColor=colors.HexColor('#2E7D32'),
        spaceBefore=12,
        spaceAfter=6
    )

    h2_style = ParagraphStyle(
        'SectionH2',
        parent=styles['Heading3'],
        fontName='Helvetica-Bold',
        fontSize=10.5,
        leading=14,
        textColor=colors.HexColor('#2D3748'),
        spaceBefore=8,
        spaceAfter=4
    )

    body_style = ParagraphStyle(
        'BodyTextCustom',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=13,
        textColor=colors.HexColor('#2D3748'),
        spaceAfter=6
    )

    table_header_style = ParagraphStyle(
        'TableHeader',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8,
        leading=10,
        textColor=colors.white
    )

    table_cell_style = ParagraphStyle(
        'TableCell',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8,
        leading=11,
        textColor=colors.HexColor('#1A202C')
    )

    story = []

    # Title & Metadata block
    story.append(Paragraph("AUTOSAR High-Level Design (HLD) Specification", title_style))
    story.append(Paragraph("Domain: Powertrain & Chassis Control Domain | Release 2.0 (ADAS & Defect Remediation)", subtitle_style))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor('#2E7D32'), spaceAfter=10))

    meta_data = [
        [Paragraph("<b>Document ID:</b> DOC-AUTOSAR-PT-V2", table_cell_style),
         Paragraph("<b>Target ECU:</b> TriCore TC397x (Domain Controller)", table_cell_style)],
        [Paragraph("<b>Standard:</b> AUTOSAR Classic Platform 4.4.0", table_cell_style),
         Paragraph("<b>Classification:</b> ASIL-D / ISO 26262", table_cell_style)],
        [Paragraph("<b>Author:</b> Powertrain Architecture Guild", table_cell_style),
         Paragraph("<b>Release Date:</b> 2026-06-20 (Revision 2.0)", table_cell_style)],
    ]
    meta_table = Table(meta_data, colWidths=[250, 250])
    meta_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#E8F5E9')),
        ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#A5D6A7')),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#C8E6C9')),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    story.append(meta_table)
    story.append(Spacer(1, 12))

    # Section 1: Overview
    story.append(Paragraph("1. System Architecture Overview & Revision Summary", h1_style))
    story.append(Paragraph(
        "Revision 2.0 introduces ADAS Level-2 integration by incorporating <code>LaneKeepAssistSWC</code>, "
        "resolves the undefined provider dependency for throttle signals via <code>PedalInterfaceSWC</code>, "
        "formally declares <code>SteeringAngleSensorSWC</code>, and corrects the data-type mismatch on the "
        "battery current interface between <code>BatteryManagementSWC</code> and <code>TransmissionControlSWC</code>.",
        body_style
    ))

    # Section 2: BrakeControlSWC
    story.append(Paragraph("2. Software Component: BrakeControlSWC", h1_style))
    story.append(Paragraph(
        "<b>Component Type:</b> Application Software Component (ApplicationSWC)<br/>"
        "<b>Execution Periodicity:</b> 10ms | <b>Safety Level:</b> ASIL-D<br/>"
        "<b>Description:</b> Responsible for friction braking, regenerative braking demand, and ADAS emergency deceleration blending.",
        body_style
    ))

    bc_ports_v2 = [
        [Paragraph("Port Name", table_header_style), Paragraph("Port Type", table_header_style),
         Paragraph("Interface Name", table_header_style), Paragraph("Signal / Element", table_header_style),
         Paragraph("Data Type", table_header_style), Paragraph("Target / Provider", table_header_style)],
        [Paragraph("RPort_VehicleSpeed", table_cell_style), Paragraph("R-Port (Require)", table_cell_style),
         Paragraph("If_VehicleSpeed", table_cell_style), Paragraph("VehicleSpeed_kph", table_cell_style),
         Paragraph("float32", table_cell_style), Paragraph("WheelSpeedSensorSWC", table_cell_style)],
        [Paragraph("PPort_BrakeTorqueRequest", table_cell_style), Paragraph("P-Port (Provide)", table_cell_style),
         Paragraph("If_BrakeTorque", table_cell_style), Paragraph("BrakeTorque_Nm", table_cell_style),
         Paragraph("uint16", table_cell_style), Paragraph("EngineManagerSWC", table_cell_style)],
        [Paragraph("RPort_SteeringAngle", table_cell_style), Paragraph("R-Port (Require)", table_cell_style),
         Paragraph("If_SteeringAngle", table_cell_style), Paragraph("SteeringAngle_deg", table_cell_style),
         Paragraph("float32", table_cell_style), Paragraph("SteeringAngleSensorSWC", table_cell_style)],
        [Paragraph("RPort_ADASEmergencyBrake", table_cell_style), Paragraph("R-Port (Require)", table_cell_style),
         Paragraph("If_ADASDecelRequest", table_cell_style), Paragraph("DecelRequest_mps2", table_cell_style),
         Paragraph("float32", table_cell_style), Paragraph("LaneKeepAssistSWC", table_cell_style)],
    ]
    t_bc_v2 = Table(bc_ports_v2, colWidths=[95, 75, 80, 85, 55, 110])
    t_bc_v2.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2E7D32')),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E0')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F7FAFC')]),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
    ]))
    story.append(t_bc_v2)
    story.append(Spacer(1, 8))

    # Section 3: SteeringAngleSensorSWC (Newly Defined in V2)
    story.append(Paragraph("3. Software Component: SteeringAngleSensorSWC (NEW)", h1_style))
    story.append(Paragraph(
        "<b>Component Type:</b> Sensor/Actuator Software Component (SensorActuatorSWC)<br/>"
        "<b>Execution Periodicity:</b> 10ms | <b>Safety Level:</b> ASIL-D<br/>"
        "<b>Description:</b> Calibrates and transmits real-time steering wheel angular position and rotational velocity.",
        body_style
    ))
    sas_ports = [
        [Paragraph("Port Name", table_header_style), Paragraph("Port Type", table_header_style),
         Paragraph("Interface Name", table_header_style), Paragraph("Signal / Element", table_header_style),
         Paragraph("Data Type", table_header_style), Paragraph("Target / Provider", table_header_style)],
        [Paragraph("PPort_SteeringAngle", table_cell_style), Paragraph("P-Port (Provide)", table_cell_style),
         Paragraph("If_SteeringAngle", table_cell_style), Paragraph("SteeringAngle_deg", table_cell_style),
         Paragraph("float32", table_cell_style), Paragraph("BrakeControlSWC, LaneKeepAssistSWC", table_cell_style)],
    ]
    t_sas = Table(sas_ports, colWidths=[95, 75, 80, 85, 55, 110])
    t_sas.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2E7D32')),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E0')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F7FAFC')]),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
    ]))
    story.append(t_sas)
    story.append(Spacer(1, 8))

    # Page Break for Page 2
    story.append(PageBreak())

    # Section 4: PedalInterfaceSWC (NEW in V2)
    story.append(Paragraph("4. Software Component: PedalInterfaceSWC (NEW)", h1_style))
    story.append(Paragraph(
        "<b>Component Type:</b> Sensor/Actuator Software Component (SensorActuatorSWC)<br/>"
        "<b>Execution Periodicity:</b> 5ms | <b>Safety Level:</b> ASIL-B<br/>"
        "<b>Description:</b> Acquires dual-channel accelerator pedal potentiometers and broadcasts plausibility-checked throttle demand.",
        body_style
    ))
    pedal_ports = [
        [Paragraph("Port Name", table_header_style), Paragraph("Port Type", table_header_style),
         Paragraph("Interface Name", table_header_style), Paragraph("Signal / Element", table_header_style),
         Paragraph("Data Type", table_header_style), Paragraph("Target / Provider", table_header_style)],
        [Paragraph("PPort_ThrottleDemand", table_cell_style), Paragraph("P-Port (Provide)", table_cell_style),
         Paragraph("If_ThrottleDemand", table_cell_style), Paragraph("ThrottlePercent", table_cell_style),
         Paragraph("uint8", table_cell_style), Paragraph("EngineManagerSWC", table_cell_style)],
    ]
    t_pedal = Table(pedal_ports, colWidths=[95, 75, 80, 85, 55, 110])
    t_pedal.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2E7D32')),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E0')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F7FAFC')]),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
    ]))
    story.append(t_pedal)
    story.append(Spacer(1, 8))

    # Section 5: LaneKeepAssistSWC (NEW ADAS SWC)
    story.append(Paragraph("5. Software Component: LaneKeepAssistSWC (NEW)", h1_style))
    story.append(Paragraph(
        "<b>Component Type:</b> Application Software Component (ApplicationSWC)<br/>"
        "<b>Execution Periodicity:</b> 20ms | <b>Safety Level:</b> ASIL-D<br/>"
        "<b>Description:</b> Processes front-facing camera lane boundaries, monitors driver steering torque, and requests autonomous corrective braking or steering torque.",
        body_style
    ))
    lka_ports = [
        [Paragraph("Port Name", table_header_style), Paragraph("Port Type", table_header_style),
         Paragraph("Interface Name", table_header_style), Paragraph("Signal / Element", table_header_style),
         Paragraph("Data Type", table_header_style), Paragraph("Target / Provider", table_header_style)],
        [Paragraph("RPort_SteeringAngle", table_cell_style), Paragraph("R-Port (Require)", table_cell_style),
         Paragraph("If_SteeringAngle", table_cell_style), Paragraph("SteeringAngle_deg", table_cell_style),
         Paragraph("float32", table_cell_style), Paragraph("SteeringAngleSensorSWC", table_cell_style)],
        [Paragraph("PPort_ADASDecelRequest", table_cell_style), Paragraph("P-Port (Provide)", table_cell_style),
         Paragraph("If_ADASDecelRequest", table_cell_style), Paragraph("DecelRequest_mps2", table_cell_style),
         Paragraph("float32", table_cell_style), Paragraph("BrakeControlSWC", table_cell_style)],
    ]
    t_lka = Table(lka_ports, colWidths=[95, 75, 80, 85, 55, 110])
    t_lka.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2E7D32')),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E0')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F7FAFC')]),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
    ]))
    story.append(t_lka)
    story.append(Spacer(1, 8))

    # Section 6: TransmissionControlSWC (MODIFIED / FIXED)
    story.append(Paragraph("6. Software Component: TransmissionControlSWC (UPDATED)", h1_style))
    story.append(Paragraph(
        "<b>Component Type:</b> Application Software Component (ApplicationSWC)<br/>"
        "<b>Execution Periodicity:</b> 20ms | <b>Safety Level:</b> ASIL-C<br/>"
        "<b>Description:</b> Corrected <code>RPort_BatteryCurrent</code> data type from <code>float32</code> to <code>uint16</code> matching <code>BatteryManagementSWC</code>.",
        body_style
    ))
    tcu_ports_v2 = [
        [Paragraph("Port Name", table_header_style), Paragraph("Port Type", table_header_style),
         Paragraph("Interface Name", table_header_style), Paragraph("Signal / Element", table_header_style),
         Paragraph("Data Type", table_header_style), Paragraph("Target / Provider", table_header_style)],
        [Paragraph("RPort_EngineSpeed", table_cell_style), Paragraph("R-Port (Require)", table_cell_style),
         Paragraph("If_EngineSpeed", table_cell_style), Paragraph("EngineSpeed_rpm", table_cell_style),
         Paragraph("uint16", table_cell_style), Paragraph("EngineManagerSWC", table_cell_style)],
        [Paragraph("RPort_BatteryCurrent", table_cell_style), Paragraph("R-Port (Require)", table_cell_style),
         Paragraph("If_BatteryCurrent", table_cell_style), Paragraph("Current_A", table_cell_style),
         Paragraph("uint16", table_cell_style), Paragraph("BatteryManagementSWC", table_cell_style)],
        [Paragraph("PPort_GearPosition", table_cell_style), Paragraph("P-Port (Provide)", table_cell_style),
         Paragraph("If_GearStatus", table_cell_style), Paragraph("CurrentGear", table_cell_style),
         Paragraph("uint8", table_cell_style), Paragraph("InstrumentClusterSWC", table_cell_style)],
    ]
    t_tcu_v2 = Table(tcu_ports_v2, colWidths=[95, 75, 80, 85, 55, 110])
    t_tcu_v2.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2E7D32')),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E0')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F7FAFC')]),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
    ]))
    story.append(t_tcu_v2)

    doc.build(story, onFirstPage=create_header_footer, onLaterPages=create_header_footer)
    print(f"Generated sample HLD V2 at {output_path}")


if __name__ == "__main__":
    output_dir = os.path.dirname(os.path.abspath(__file__))
    v1_path = os.path.join(output_dir, "sample_autosar_hld_v1.pdf")
    v2_path = os.path.join(output_dir, "sample_autosar_hld_v2.pdf")
    build_v1_pdf(v1_path)
    build_v2_pdf(v2_path)
