import ReactFlow, { ReactFlowProvider } from "reactflow"
import "reactflow/dist/style.css"
import { useEffect, useState } from "react"

export default function Diagram({ nodes, links }) {

    const [flowNodes, setFlowNodes] = useState([])
    const [flowEdges, setFlowEdges] = useState([])

    useEffect(() => {

        const formattedNodes = nodes.map((n, i) => ({
            id: String(n.id),

            data: {
                label: (
                    <div style={{
                        padding: "10px",
                        fontSize: "14px",
                        fontWeight: "500",
                        textAlign: "center"
                    }}>
                        {n.label
                            .replace(/\*\*/g, "")     // remove **
                            .replace(/\*/g, "")       // remove *
                            .replace(/Step\d:/gi, "") // remove Step1:
                            .replace(/\s+/g, " ")     // clean spaces
                            .trim()
                        }
                    </div>
                )
            },

            position: { x: 100 + i * 250, y: 150 },

            style: {
                background: "#1e293b",
                color: "white",
                borderRadius: "12px",
                border: "1px solid #38bdf8",
                padding: "5px",
                minWidth: "150px"
            }
        }))

        const formattedEdges = links.map((l, i) => ({
            id: "e" + i,
            source: String(l.source),
            target: String(l.target),
            animated: true,
            style: { stroke: "#38bdf8" }
        }))

        setFlowNodes(formattedNodes)
        setFlowEdges(formattedEdges)

    }, [nodes, links])

    return (
        <div style={{
            height: "100%",
            width: "100%",
            background: "#0f172a",
            borderRadius: "12px"
        }}>
            <ReactFlowProvider>
                <ReactFlow
                    nodes={flowNodes}
                    edges={flowEdges}
                    fitView
                    fitViewOptions={{ padding: 0.2 }}
                />
            </ReactFlowProvider>
        </div>
    )
}