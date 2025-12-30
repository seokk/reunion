# JSON Schema for OpenAI Structured Output
# 재회 확률 분석 결과의 구조화된 응답 스키마

REUNION_ANALYSIS_SCHEMA = {
    "type": "object",
    "properties": {
        # 1. 전체 재회 확률 (1-100)
        "overall_probability": {
            "type": "number",
            "description": "전체 재회 가능 확률 (1-100)"
        },

        # 2. 요인별 분석
        "factor_analysis": {
            "type": "object",
            "properties": {
                "emotional": {
                    "type": "object",
                    "properties": {
                        "score": {
                            "type": "number",
                            "description": "감정적 요인 점수 (1-100)"
                        },
                        "analysis": {
                            "type": "string",
                            "description": "감정적 요인에 대한 상세 분석. 200자 내외로 작성."
                        }
                    },
                    "required": ["score", "analysis"],
                    "additionalProperties": False
                },
                "psychological": {
                    "type": "object",
                    "properties": {
                        "score": {
                            "type": "number",
                            "description": "심리적 요인 점수 (1-100)"
                        },
                        "analysis": {
                            "type": "string",
                            "description": "심리적 요인(성격, MBTI, 애착유형)에 대한 상세 분석. 200자 내외로 작성."
                        }
                    },
                    "required": ["score", "analysis"],
                    "additionalProperties": False
                },
                "environmental": {
                    "type": "object",
                    "properties": {
                        "score": {
                            "type": "number",
                            "description": "환경적 요인 점수 (1-100)"
                        },
                        "analysis": {
                            "type": "string",
                            "description": "환경적 요인(거리, 연락상태)에 대한 상세 분석. 200자 내외로 작성."
                        }
                    },
                    "required": ["score", "analysis"],
                    "additionalProperties": False
                },
                "other": {
                    "type": "object",
                    "properties": {
                        "score": {
                            "type": "number",
                            "description": "기타 요인 점수 (1-100)"
                        },
                        "analysis": {
                            "type": "string",
                            "description": "기타 요인(나이, 나이차이)에 대한 상세 분석. 300자 내외로 작성."
                        }
                    },
                    "required": ["score", "analysis"],
                    "additionalProperties": False
                }
            },
            "required": ["emotional", "psychological", "environmental", "other"],
            "additionalProperties": False
        },

        # 3. 상대방 심리 추측
        "partner_psychology": {
            "type": "object",
            "properties": {
                "breakup_reason_analysis": {
                    "type": "string",
                    "description": "이별 사유에 따른 상대방의 현재 상황 분석. 350자 이내."
                },
                "personality_analysis": {
                    "type": "string",
                    "description": "상대방의 성격 키워드에 따른 현재 심리 분석. 350자 이내."
                },
                "reunion_willingness": {
                    "type": "string",
                    "description": "상대방이 현재 재회를 원하는 상태인지에 대한 추측. 350자 이내."
                }
            },
            "required": ["breakup_reason_analysis", "personality_analysis", "reunion_willingness"],
            "additionalProperties": False
        },

        # 4. 재회 필요 요소
        "reunion_requirements": {
            "type": "object",
            "properties": {
                "solution": {
                    "type": "string",
                    "description": "재회를 위한 핵심 솔루션. 300자 이내."
                },
                "contact_timing": {
                    "type": "string",
                    "description": "연락하기 좋은 시점과 이유. 300자 이내."
                },
                "approach_stance": {
                    "type": "string",
                    "description": "어떤 스탠스를 취해야 하는지. 300자 이내."
                },
                "contact_method": {
                    "type": "string",
                    "description": "어떤 형태로 연락하는 게 좋을지. 300자 이내."
                },
                "considerations": {
                    "type": "array",
                    "description": "연락하기 전 고려해봐야 할 요소들. 각 항목은 100자 이내.",
                    "items": {
                        "type": "string"
                    },
                    "minItems": 3,
                    "maxItems": 4
                }
            },
            "required": ["solution", "contact_timing", "approach_stance", "contact_method", "considerations"],
            "additionalProperties": False
        },

        # 5. 재회 후 관계 유지
        "relationship_maintenance": {
            "type": "object",
            "properties": {
                "introduction": {
                    "type": "string",
                    "description": "관계 유지의 중요성에 대한 서론. 200자 이내."
                },
                "tips": {
                    "type": "array",
                    "description": "관계 유지를 위한 구체적인 팁들",
                    "items": {
                        "type": "object",
                        "properties": {
                            "title": {
                                "type": "string",
                                "description": "팁 제목. 15자 이내. 예: '정기적인 감정 점검'"
                            },
                            "description": {
                                "type": "string",
                                "description": "팁에 대한 상세 설명. 200자 내외."
                            }
                        },
                        "required": ["title", "description"],
                        "additionalProperties": False
                    },
                    "minItems": 4,
                    "maxItems": 5
                }
            },
            "required": ["introduction", "tips"],
            "additionalProperties": False
        },

        # 6. 최종 조언
        "final_advice": {
            "type": "object",
            "properties": {
                "approach_method": {
                    "type": "string",
                    "description": "어떤 접근 방식이 좋을지 (직접적/우회적/단계적 등). 300자 이내."
                },
                "emotion_expression": {
                    "type": "string",
                    "description": "감정 표현은 어떻게 하는 게 좋을지. 300자 이내."
                },
                "optimal_timing": {
                    "type": "string",
                    "description": "어느 시점에 연락하는 게 좋을지 구체적인 조언. 300자 이내."
                }
            },
            "required": ["approach_method", "emotion_expression", "optimal_timing"],
            "additionalProperties": False
        }
    },
    "required": [
        "overall_probability",
        "factor_analysis",
        "partner_psychology",
        "reunion_requirements",
        "relationship_maintenance",
        "final_advice"
    ],
    "additionalProperties": False
}
